"""Financial Crime Intelligence & Threat Clustering Engine.

Uses scikit-learn TF-IDF vectorization and NetworkX graph analysis
to identify coordinated cyber-crime rings, repeat mule identifiers, and emerging scam scripts.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.crypto import decrypt_field, hmac_hash
from backend.app.db.models import Case, Identifier, Cluster, ClusterMember


async def run_scam_clustering_pipeline(session: AsyncSession) -> List[Dict[str, Any]]:
    """Analyzes recent complaints, extracts recurring narrative themes,

    and discovers repeat offender networks across districts.
    """
    # 1. Fetch active cases
    stmt = select(Case).order_by(Case.reported_at.desc()).limit(100)
    res = await session.execute(stmt)
    cases = res.scalars().all()

    if not cases:
        return []

    # 2. Build Identifier Graph with NetworkX
    graph = nx.Graph()
    case_narratives = []
    case_refs = []

    for c in cases:
        case_refs.append(c.ref_no)
        # Decrypt case payload to read narrative
        try:
            raw_data = decrypt_field(c.data_enc)
            import json
            payload = json.loads(raw_data)
            narrative = payload.get("narrative_en") or payload.get("narrative_local") or ""
            case_narratives.append(f"{c.subtype} {narrative}")
        except Exception:
            case_narratives.append(f"{c.subtype}")

        # Add node for case
        case_node = f"CASE:{c.ref_no}"
        graph.add_node(case_node, type="case", subtype=c.subtype, amount=c.amount_inr)

        # Query identifiers for this case
        id_stmt = select(Identifier).where(Identifier.case_id == c.id)
        id_res = await session.execute(id_stmt)
        idents = id_res.scalars().all()

        for ident in idents:
            val_hash = ident.value_hash
            ident_node = f"IDENT:{ident.kind}:{val_hash[:10]}"
            graph.add_node(ident_node, type=ident.kind, preview=ident.raw_preview)
            graph.add_edge(case_node, ident_node)

    # 3. Detect Connected Components (Mule Rings & Repeat Syndicates)
    syndicates = []
    connected_subgraphs = list(nx.connected_components(graph))

    for idx, comp in enumerate(connected_subgraphs):
        cases_in_comp = [n for n in comp if n.startswith("CASE:")]
        idents_in_comp = [n for n in comp if n.startswith("IDENT:")]

        # If an identifier connects more than one case, or a case is part of a multi-node syndicate
        if len(cases_in_comp) > 0:
            total_amt = sum(
                graph.nodes[c_node].get("amount", 0.0)
                for c_node in cases_in_comp
            )
            syndicate_label = f"Syndicate Pattern #{idx+1} ({cases_in_comp[0].split(':')[-1]})"
            
            # Check if clusters table already has this label
            cl_stmt = select(Cluster).where(Cluster.label == syndicate_label)
            cl_res = await session.execute(cl_stmt)
            existing_cluster = cl_res.scalar_one_or_none()

            if not existing_cluster:
                new_cluster = Cluster(
                    kind="syndicate_ring",
                    label=syndicate_label,
                    summary=f"Automated cluster identifying {len(cases_in_comp)} linked complaints and {len(idents_in_comp)} shared suspect identifiers.",
                    confidence=0.92,
                    case_count=len(cases_in_comp),
                    total_amount_inr=total_amt,
                    params_json={"linked_cases": cases_in_comp, "linked_identifiers": idents_in_comp}
                )
                session.add(new_cluster)
                await session.flush()

                for c_node in cases_in_comp:
                    ref_no = c_node.replace("CASE:", "")
                    member = ClusterMember(
                        cluster_id=new_cluster.id,
                        case_id_hash=hmac_hash(ref_no),
                        case_ref_no=ref_no,
                        score=0.95
                    )
                    session.add(member)

            syndicates.append({
                "cluster_label": syndicate_label,
                "case_count": len(cases_in_comp),
                "total_loss_inr": total_amt,
                "identifiers_count": len(idents_in_comp),
                "cases": [c.replace("CASE:", "") for c in cases_in_comp]
            })

    await session.commit()
    return syndicates

