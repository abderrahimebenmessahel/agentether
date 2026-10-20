"""AgenTether - a supervisor wrapper around a single LLM worker call.

AgenTether keeps the *control path* (roadmap, state, limits, validation) in
deterministic code and on disk, and treats the LLM's text as an untrusted
*data path*.  It is not a multi-agent framework: it supervises one worker
function, one step at a time.

Typical use::

    from agentether import AutoOrchestrator, artifacts_exist

    orch = AutoOrchestrator(
        roadmap=["research", "write"],
        memory_dir="./memory",
        timeout_seconds=60,
        max_retries=3,
    )

    @orch.guard_step("research", verify=[artifacts_exist()])
    async def research(ctx):
        return await my_llm(ctx.build_prompt("Research X"))

    result = await research()  # StepResult with validated telemetry
    result = await research.rerun()  # ignore the cached result
"""

from __future__ import annotations

from .budget import BudgetTracker
from .events import EVENT_NAMES, EventBus, EventLog
from .exceptions import (
    AgenTetherError,
    AgentExecutionError,
    AgentTimeoutError,
    BudgetExceededError,
    CircuitBreakerOpenError,
    ConfigurationError,
    ContextDriftError,
    FailureKind,
    LoopDetectedError,
    StateCorruptionError,
    TelemetryParseError,
    VerificationFailedError,
)
from .logging_utils import ColorFormatter, configure_logging, logger
from .loop_detector import LoopDetector, StallDetector, fingerprint, jaccard, normalize
from .models import (
    ALLOWED_STATUSES,
    StepContext,
    StepResult,
    Telemetry,
    TelemetryStatus,
    Usage,
    Verifier,
    VerifyContext,
    VerifyResult,
    WorkerOutput,
)
from .orchestrator import AutoOrchestrator, GuardedStep, StepFunction, guard_step
from .parser import extract_json_telemetry, parse_telemetry
from .policy import (
    BreakerPolicy,
    BudgetPolicy,
    GuardPolicy,
    LoopPolicy,
    RetryPolicy,
    StallPolicy,
    approximate_token_count,
)
from .state_manager import StateManager
from .verifier import (
    artifacts_exist,
    callable_verifier,
    command_succeeds,
    file_contains,
    file_exists,
    json_file_valid,
    llm_judge,
)

__version__ = "0.2.0"

__all__ = [
    "ALLOWED_STATUSES",
    "EVENT_NAMES",
    "AgenTetherError",
    "AgentExecutionError",
    "AgentTimeoutError",
    "AutoOrchestrator",
    "BreakerPolicy",
    "BudgetExceededError",
    "BudgetPolicy",
    "BudgetTracker",
    "CircuitBreakerOpenError",
    "ColorFormatter",
    "ConfigurationError",
    "ContextDriftError",
    "EventBus",
    "EventLog",
    "FailureKind",
    "GuardPolicy",
    "GuardedStep",
    "LoopDetectedError",
    "LoopDetector",
    "LoopPolicy",
    "RetryPolicy",
    "StallDetector",
    "StallPolicy",
    "StateCorruptionError",
    "StateManager",
    "StepContext",
    "StepFunction",
    "StepResult",
    "Telemetry",
    "TelemetryParseError",
    "TelemetryStatus",
    "Usage",
    "VerificationFailedError",
    "Verifier",
    "VerifyContext",
    "VerifyResult",
    "WorkerOutput",
    "__version__",
    "approximate_token_count",
    "artifacts_exist",
    "callable_verifier",
    "command_succeeds",
    "configure_logging",
    "extract_json_telemetry",
    "file_contains",
    "file_exists",
    "fingerprint",
    "guard_step",
    "jaccard",
    "json_file_valid",
    "llm_judge",
    "logger",
    "normalize",
    "parse_telemetry",
]
