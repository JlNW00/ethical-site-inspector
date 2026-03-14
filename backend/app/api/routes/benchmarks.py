"""API routes for Benchmark endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal, get_db
from app.models import Benchmark
from app.schemas.benchmark import BenchmarkCreate, BenchmarkRead
from app.services.audit_orchestrator import AuditOrchestrator
from app.services.benchmark_orchestrator import BenchmarkOrchestrator

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])

# Initialize orchestrators
audit_orchestrator = AuditOrchestrator(SessionLocal)
benchmark_orchestrator = BenchmarkOrchestrator(SessionLocal, audit_orchestrator)


@router.get("", response_model=list[BenchmarkRead])
def list_benchmarks(
    db: Session = Depends(get_db),  # noqa: B008
    status: Annotated[str | None, Query(description="Filter by benchmark status")] = None,
) -> list[Benchmark]:
    """List all benchmarks sorted by created_at descending.

    Returns an array of benchmarks.
    Supports optional query params:
    - status: Filter by status (queued, running, completed, failed)
    """
    statement = select(Benchmark).order_by(desc(Benchmark.created_at))

    if status:
        statement = statement.where(Benchmark.status == status)

    benchmarks = db.scalars(statement).all()
    return list(benchmarks)


@router.post("", response_model=BenchmarkRead, status_code=status.HTTP_201_CREATED)
def create_benchmark(
    payload: BenchmarkCreate,
    db: Session = Depends(get_db),  # noqa: B008
) -> Benchmark:
    """Create a new benchmark with 2-5 URLs.

    Spawns individual audits per URL and returns the benchmark object.
    Validation:
    - URLs must be 2-5 unique valid HTTP/HTTPS URLs
    - selected_scenarios must be valid scenario types
    - selected_personas must be valid persona types
    """
    settings = get_settings()
    benchmark = benchmark_orchestrator.create_benchmark(db, payload, mode=settings.effective_mode)
    # Launch audits in background
    benchmark_orchestrator.launch_benchmark(benchmark.id)
    return benchmark


@router.get("/{benchmark_id}", response_model=BenchmarkRead)
def get_benchmark(
    benchmark_id: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> Benchmark:
    """Get a single benchmark by ID.

    Returns the full benchmark object including:
    - id: UUID
    - status: queued|running|completed|failed
    - urls: ordered list of URLs
    - audit_ids: ordered list of audit IDs (matching urls order)
    - trust_scores: dict mapping URL to trust score (populated after completion)
    - created_at, updated_at: timestamps
    """
    statement = select(Benchmark).where(Benchmark.id == benchmark_id)
    benchmark = db.scalar(statement)
    if benchmark is None:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    return benchmark
