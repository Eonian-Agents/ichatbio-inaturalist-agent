from instructor.exceptions import InstructorRetryException
from pydantic_core import ValidationError
from tenacity import RetryCallState
from tenacity.stop import stop_base


def _get_terminal_validation_error(e: Exception):
    if isinstance(e, ValidationError):
        for error in e.errors():
            if error.get("ctx", {}).get("terminal", False):
                return error
    return None


class AIGenerationException(Exception):
    def __init__(self, e: InstructorRetryException):
        messages = []
        terminal_error = _get_terminal_validation_error(e)
        if terminal_error:
            messages.append(f"Error: {terminal_error['msg']}")
        else:
            messages.append(f"Error: AI failed to generate valid output after {e.n_attempts} attempts.")

        self.message = "\n\n".join(messages)
        super().__init__(self.message)


class StopOnTerminalErrorOrMaxAttempts(stop_base):
    """Stop when a bad value is encountered."""

    def __init__(self, max_attempts: int):
        self.max_attempts = max_attempts

    def __call__(self, retry_state: RetryCallState) -> bool:
        exception = retry_state.outcome.exception()
        if _get_terminal_validation_error(exception):
            return True
        else:
            return retry_state.attempt_number >= self.max_attempts
