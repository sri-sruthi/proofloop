# AWS SAM invokes these targets with ARTIFACTS_DIR.  Keep source and dependency
# installation separate so the build contains only the package and runtime deps.
PYTHON ?= python3
PROJECT_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
PYPROJECT := $(PROJECT_ROOT)/pyproject.toml

.PHONY: build-ProofLoopApiFunction build-ProofLoopScheduledFunction

define build_runtime
	@mkdir -p "$(ARTIFACTS_DIR)"
	$(PYTHON) -c 'import subprocess, sys, tomllib; project = tomllib.load(open(sys.argv[1], "rb")); subprocess.check_call([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-compile", "--target", sys.argv[2], *project["project"]["dependencies"]])' "$(PYPROJECT)" "$(ARTIFACTS_DIR)"
	cp -R "$(PROJECT_ROOT)/src/proofloop" "$(ARTIFACTS_DIR)/proofloop"
endef

build-ProofLoopApiFunction:
	$(build_runtime)

build-ProofLoopScheduledFunction:
	$(build_runtime)
