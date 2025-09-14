# compiler/opcodes.py
from __future__ import annotations

# Task-agnostic opcodes for AIOX VM (v2)
OPCODES = [
    # Tool System (v2) - Unified dynamic dispatch
    "CALL_TOOL",        # tool_name, inputs_dict, outputs_dict -> (executes tool)

    # Legacy opcodes (v1) - Keep for backward compatibility during transition
    # data I/O + transforms
    "READ_CSV",         # in_path -> tbl_slot
    "PROFILE",          # tbl_slot -> schema_slot
    "SPLIT",            # tbl_slot, ratio, seed -> train_slot, val_slot
    "TRAIN_LR",         # train_slot, target -> model_slot
    "EVAL",             # model_slot, val_slot -> metrics_slot

    # file emission / packaging
    "EMIT_REPORT",      # schema_slot, metrics_slot, out_path -> (writes file)
    "BUILD_CLI",        # model_slot, schema_slot, out_dir -> (writes files)
    "ZIP",              # src_dir, dest_zip -> (writes zip)

    # verification / control
    "VERIFY_ZIP",       # zip_path -> ok
    "VERIFY_CLI",       # app_dir, sample_json_path -> ok
    "ASSERT_GE",        # slot, field, threshold -> ok or HALT

    # filesystem utils (used later by runtime)
    "WRITE_FILE",       # path, bytes/text
    "WRITE_JSON",       # path, json
    "MAKE_DIR",         # path
]

OP_SET = set(OPCODES)

# Legacy opcode to tool name mapping
LEGACY_TO_TOOL = {
    "READ_CSV": "read_csv",
    "PROFILE": "profile",
    "SPLIT": "split",
    "TRAIN_LR": "train_lr",
    "EVAL": "eval",
    "EMIT_REPORT": "emit_report",
    "BUILD_CLI": "build_cli",
    "ZIP": "zip",
    "VERIFY_ZIP": "verify_zip",
    "VERIFY_CLI": "verify_cli",
    "ASSERT_GE": "assert_ge",
}