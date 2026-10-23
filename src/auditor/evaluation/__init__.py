"""Auditor evaluation framework and benchmark comparison harness."""

from auditor.evaluation.manifest import (
    AnnotationState,
    BenchmarkManifest,
    ManifestCase,
    load_benchmark_manifest,
)
from auditor.evaluation.metrics import (
    CaseEvaluationDetail,
    ConfigurationMetrics,
    compute_configuration_metrics,
)
from auditor.evaluation.provenance import (
    CaseProvenanceRecord,
    ResultProvenance,
    determine_case_eligibility,
)
from auditor.evaluation.report_generator import EvaluationReportGenerator
from auditor.evaluation.runner import ConfigurationRunOutput, EvaluationRunner

__all__ = [
    "AnnotationState",
    "BenchmarkManifest",
    "CaseEvaluationDetail",
    "CaseProvenanceRecord",
    "ConfigurationMetrics",
    "ConfigurationRunOutput",
    "EvaluationReportGenerator",
    "EvaluationRunner",
    "ManifestCase",
    "ResultProvenance",
    "compute_configuration_metrics",
    "determine_case_eligibility",
    "load_benchmark_manifest",
]
