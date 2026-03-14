"""Benchmark orchestrator service for managing multi-URL comparison audits."""

from __future__ import annotations

from collections.abc import Callable
from threading import Thread

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Audit, Benchmark
from app.schemas.audit import AuditCreateRequest
from app.schemas.benchmark import BenchmarkCreate
from app.services.audit_orchestrator import AuditOrchestrator


class BenchmarkOrchestrator:
    """Orchestrates the creation and execution of benchmark audits.

    A benchmark spawns individual audits per URL and aggregates their results.
    """

    def __init__(self, session_factory: Callable[[], Session], audit_orchestrator: AuditOrchestrator | None = None) -> None:
        self.session_factory = session_factory
        self.audit_orchestrator = audit_orchestrator or AuditOrchestrator(session_factory)

    def create_benchmark(
        self,
        db: Session,
        payload: BenchmarkCreate,
        mode: str,
    ) -> Benchmark:
        """Create a new benchmark and spawn individual audits per URL.

        Args:
            db: Database session
            payload: Benchmark creation request with URLs, scenarios, and personas
            mode: Audit mode (mock, hybrid, live)

        Returns:
            The created Benchmark object with audit_ids populated
        """
        # Create the benchmark record
        benchmark = Benchmark(
            status="queued",
            urls=[str(url) for url in payload.urls],
            audit_ids=[],
            trust_scores=None,
            selected_scenarios=list(payload.selected_scenarios),
            selected_personas=list(payload.selected_personas),
        )
        db.add(benchmark)
        db.flush()

        # Create individual audits for each URL
        audit_ids = []
        for url in payload.urls:
            audit_payload = AuditCreateRequest(
                target_url=url,
                scenarios=payload.selected_scenarios,
                personas=payload.selected_personas,
            )
            audit = self.audit_orchestrator.create_audit(db, audit_payload, mode=mode)
            audit_ids.append(audit.id)

        # Update benchmark with audit_ids (preserving order)
        benchmark.audit_ids = audit_ids
        db.commit()
        db.refresh(benchmark)

        return self.get_benchmark(db, benchmark.id)

    def launch_benchmark(self, benchmark_id: str, mode_override: str | None = None) -> None:
        """Launch all audits for a benchmark in background threads.

        Args:
            benchmark_id: The benchmark ID to launch
            mode_override: Optional mode override for audits
        """
        Thread(target=self._run_benchmark, args=(benchmark_id, mode_override), daemon=True).start()

    def _run_benchmark(self, benchmark_id: str, mode_override: str | None = None) -> None:
        """Internal method to run all audits and track progress.

        Updates benchmark status as audits complete and aggregates trust_scores.
        """
        try:
            self._run_benchmark_internal(benchmark_id, mode_override)
        except Exception as exc:
            self._handle_benchmark_failure(benchmark_id, exc)

    def _run_benchmark_internal(self, benchmark_id: str, mode_override: str | None = None) -> None:
        """Execute all audits for the benchmark sequentially."""
        with self.session_factory() as db:
            benchmark = self.get_benchmark(db, benchmark_id)
            benchmark.status = "running"
            db.commit()

        # Launch each audit sequentially
        all_completed = True
        trust_scores: dict[str, float] = {}

        for audit_id in benchmark.audit_ids:
            # Launch the audit
            self.audit_orchestrator.launch_audit(audit_id, mode_override)

            # Wait for audit to complete (poll status)
            trust_score = self._wait_for_audit_and_get_score(audit_id)
            if trust_score is not None:
                # Find the URL for this audit
                with self.session_factory() as db:
                    audit = db.scalar(select(Audit).where(Audit.id == audit_id))
                    if audit:
                        trust_scores[audit.target_url] = trust_score
            else:
                all_completed = False

        # Update benchmark status and trust_scores
        with self.session_factory() as db:
            benchmark = self.get_benchmark(db, benchmark_id)
            if all_completed:
                benchmark.status = "completed"
            else:
                # Some audits may have failed, but we still mark as completed
                # with partial results (frontend handles mixed states)
                benchmark.status = "completed"
            benchmark.trust_scores = trust_scores if trust_scores else None
            db.commit()

    def _wait_for_audit_and_get_score(self, audit_id: str) -> float | None:
        """Wait for an audit to complete and return its trust score.

        Polls the audit status until it completes or fails.
        Returns the trust score if completed, None if failed.
        """

        max_wait = 600  # 10 minutes max wait
        poll_interval = 1.0  # 1 second polling
        elapsed = 0.0

        while elapsed < max_wait:
            with self.session_factory() as db:
                audit = db.scalar(select(Audit).where(Audit.id == audit_id))
                if audit is None:
                    return None

                if audit.status == "completed":
                    return audit.trust_score

                if audit.status == "failed":
                    return None

            # Use mypy-compatible cast to handle the float return type
            import time as _time
            _time.sleep(poll_interval)
            elapsed += poll_interval

        # Timeout - return None explicitly typed
        result: float | None = None
        return result

    def _handle_benchmark_failure(self, benchmark_id: str, exc: Exception) -> None:
        """Handle terminal benchmark failure."""
        try:
            with self.session_factory() as db:
                benchmark = self.get_benchmark(db, benchmark_id)
                benchmark.status = "failed"
                db.commit()
        except Exception:
            # Last resort - log error
            import logging

            logger = logging.getLogger(__name__)
            logger.critical(f"Failed to update benchmark {benchmark_id} status to failed")

    def get_benchmark(self, db: Session, benchmark_id: str) -> Benchmark:
        """Get a benchmark by ID.

        Args:
            db: Database session
            benchmark_id: The benchmark ID to retrieve

        Returns:
            The Benchmark object

        Raises:
            ValueError: If benchmark not found
        """
        statement = select(Benchmark).where(Benchmark.id == benchmark_id)
        benchmark = db.scalar(statement)
        if benchmark is None:
            raise ValueError(f"Benchmark {benchmark_id} not found")
        return benchmark

    def list_benchmarks(
        self,
        db: Session,
        status: str | None = None,
    ) -> list[Benchmark]:
        """List all benchmarks sorted by created_at descending.

        Args:
            db: Database session
            status: Optional status filter

        Returns:
            List of Benchmark objects
        """
        from sqlalchemy import desc

        statement = select(Benchmark).order_by(desc(Benchmark.created_at))

        if status:
            statement = statement.where(Benchmark.status == status)

        return list(db.scalars(statement).all())
