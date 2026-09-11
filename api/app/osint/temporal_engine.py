"""
BHOOMI NEXUS - OSINT / Public-Source Land Intelligence
Temporal Engine - Multi-Year Chronological & Physical Evidence Reconstruction

Tracks property timelines (mutations, revenue records, satellite observations, notifications)
across multi-year epochs (e.g., 2018-2024), detecting temporal anomalies, sequence violations,
and physical vs. administrative divergence.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from app.osint.schemas import TimelineEvent, GeospatialObservation, ProvenanceLevel


class TemporalTimelineEngine:
    """
    Constructs an integrated chronological timeline of administrative and
    physical events for a land parcel and scans for temporal anomalies.
    """

    def build_timeline(
        self,
        parcel_id: str,
        revenue_mutations: Optional[List[Dict[str, Any]]] = None,
        satellite_observations: Optional[List[GeospatialObservation]] = None,
        gazette_notifications: Optional[List[Dict[str, Any]]] = None,
        custom_events: Optional[List[Dict[str, Any]]] = None,
    ) -> List[TimelineEvent]:
        """
        Synthesizes multiple disparate sources into a unified chronological sequence.
        """
        events: List[TimelineEvent] = []

        # 1. Add revenue mutations / title transitions
        if revenue_mutations:
            for mut in revenue_mutations:
                event_date = mut.get("date") or "2020-01-01"
                year = int(event_date[:4]) if len(event_date) >= 4 and event_date[:4].isdigit() else 2020
                events.append(
                    TimelineEvent(
                        year=year,
                        event_date=event_date,
                        event_type="MUTATION",
                        title=f"Mutation Entry #{mut.get('mutation_number', 'N/A')}",
                        recorded_area_ha=mut.get("area_ha"),
                        description=mut.get("remarks") or f"Mutation recorded under {mut.get('buyer', 'transferee')}",
                        source=mut.get("source", "State Land Records Portal"),
                        provenance=ProvenanceLevel.VERIFIED_OFFICIAL_DATA,
                        significant_change_flag=mut.get("is_significant", False),
                    )
                )

        # 2. Add satellite observation epochs
        if satellite_observations:
            for obs in satellite_observations:
                obs_date = obs.observation_date
                year = int(obs_date[:4]) if len(obs_date) >= 4 and obs_date[:4].isdigit() else 2021
                ndvi_str = f", NDVI: {obs.vegetation_index_ndvi:.2f}" if obs.vegetation_index_ndvi is not None else ""
                events.append(
                    TimelineEvent(
                        year=year,
                        event_date=obs_date,
                        event_type="SATELLITE_CHANGE" if obs.built_up_structures_detected else "REMOTE_SENSING_EPOCH",
                        title=f"Satellite Imagery Observation ({obs.layer_name})",
                        description=f"Observed Land Use: {obs.observed_land_use}{ndvi_str}. Built-up: {obs.built_up_structures_detected}, Water presence: {obs.water_presence}.",
                        source=obs.source,
                        provenance=ProvenanceLevel.REPUTABLE_PUBLIC_DATASET,
                        significant_change_flag=obs.built_up_structures_detected,
                    )
                )

        # 3. Add government gazette notifications
        if gazette_notifications:
            for notif in gazette_notifications:
                n_date = notif.get("date", "2021-01-01")
                year = int(n_date[:4]) if len(n_date) >= 4 and n_date[:4].isdigit() else 2021
                events.append(
                    TimelineEvent(
                        year=year,
                        event_date=n_date,
                        event_type="GAZETTE_NOTIFICATION",
                        title=f"Notification: {notif.get('type', 'Statutory Notification')}",
                        description=notif.get("summary") or notif.get("title", ""),
                        source=notif.get("issuing_authority", "e-Gazette of India"),
                        provenance=ProvenanceLevel.PUBLIC_GOVERNMENT_DATA,
                        significant_change_flag=True,
                    )
                )

        # 4. Add custom / open dataset events
        if custom_events:
            for ev in custom_events:
                c_date = ev.get("date", "2022-01-01")
                year = int(c_date[:4]) if len(c_date) >= 4 and c_date[:4].isdigit() else 2022
                events.append(
                    TimelineEvent(
                        year=year,
                        event_date=c_date,
                        event_type=ev.get("type", "SURVEY_RECORD"),
                        title=ev.get("title", "Administrative Record Update"),
                        description=ev.get("description", ""),
                        source=ev.get("source", "Public Dataset"),
                        provenance=ev.get("provenance", ProvenanceLevel.REPUTABLE_PUBLIC_DATASET),
                        significant_change_flag=ev.get("significant", False),
                    )
                )

        # Sort chronologically by date
        events.sort(key=lambda x: x.event_date)
        return events

    def detect_temporal_anomalies(
        self, timeline: List[TimelineEvent]
    ) -> List[Dict[str, Any]]:
        """
        Scans an ordered timeline for anomalies:
        - Rapid successive transfers (< 90 days)
        - Physical construction observed before land-use conversion approval
        """
        anomalies: List[Dict[str, Any]] = []

        # Check mutation clustering (rapid successive transfers)
        mutation_events = [e for e in timeline if e.event_type == "MUTATION"]
        for i in range(len(mutation_events) - 1):
            try:
                d1 = datetime.strptime(mutation_events[i].event_date[:10], "%Y-%m-%d")
                d2 = datetime.strptime(mutation_events[i + 1].event_date[:10], "%Y-%m-%d")
                delta_days = (d2 - d1).days
                if 0 <= delta_days < 90:
                    anomalies.append({
                        "anomaly_type": "RAPID_SUCCESSIVE_MUTATIONS",
                        "severity": "HIGH",
                        "description": f"Mutations '{mutation_events[i].title}' and '{mutation_events[i + 1].title}' occurred within {delta_days} days of each other. Potential high-velocity title flipping.",
                        "event_dates": [mutation_events[i].event_date, mutation_events[i + 1].event_date],
                        "delta_days": delta_days,
                    })
            except Exception:
                continue

        # Check Physical vs. Administrative Order Sequence
        sat_built_up = [
            e for e in timeline
            if e.event_type == "SATELLITE_CHANGE" and e.significant_change_flag
        ]
        conversion_notifs = [
            e for e in timeline
            if e.event_type == "GAZETTE_NOTIFICATION"
            and ("conversion" in e.title.lower() or "diversion" in e.description.lower() or "clupa" in e.description.lower())
        ]

        if sat_built_up and conversion_notifs:
            first_built = sat_built_up[0]
            first_notif = conversion_notifs[0]
            if first_built.event_date < first_notif.event_date:
                anomalies.append({
                    "anomaly_type": "PHYSICAL_ACTIVITY_PRECEEDED_APPROVAL",
                    "severity": "MEDIUM",
                    "description": f"Satellite imagery indicated built-up structure on {first_built.event_date}, prior to official conversion notification on {first_notif.event_date}.",
                    "event_dates": [first_built.event_date, first_notif.event_date],
                })

        return anomalies
