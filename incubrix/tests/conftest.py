import os
import pytest

# Enforce deterministic fast test mode during pytest runs
os.environ["INCUBRIX_TEST_MODE"] = "1"
