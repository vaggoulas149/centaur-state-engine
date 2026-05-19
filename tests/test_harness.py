import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from centaur.harness import AssignmentPipeline


def test_pipeline_generates_all_output_files(tmp_path):
    input_dir = Path("data/input")
    output_dir = tmp_path / "output"

    pipeline = AssignmentPipeline(input_dir=input_dir, output_dir=output_dir)
    pipeline.execute_pipeline()

    expected_files = [
        "states.csv",
        "transitions_compressed.csv",
        "trades_naive.csv",
        "trades_optimal.csv",
    ]

    for filename in expected_files:
        assert (output_dir / filename).exists()


def test_generated_output_files_are_not_empty(tmp_path):
    input_dir = Path("data/input")
    output_dir = tmp_path / "output"

    pipeline = AssignmentPipeline(input_dir=input_dir, output_dir=output_dir)
    pipeline.execute_pipeline()

    for filename in [
        "states.csv",
        "transitions_compressed.csv",
        "trades_naive.csv",
        "trades_optimal.csv",
    ]:
        file_path = output_dir / filename
        assert file_path.exists()
        assert file_path.stat().st_size > 0


def test_pipeline_execution_is_deterministic(tmp_path):
    input_dir = Path("data/input")

    output_dir_a = tmp_path / "run_a"
    output_dir_b = tmp_path / "run_b"

    AssignmentPipeline(input_dir=input_dir, output_dir=output_dir_a).execute_pipeline()
    AssignmentPipeline(input_dir=input_dir, output_dir=output_dir_b).execute_pipeline()

    for filename in [
        "states.csv",
        "transitions_compressed.csv",
        "trades_naive.csv",
        "trades_optimal.csv",
    ]:
        assert (output_dir_a / filename).read_text() == (
            output_dir_b / filename
        ).read_text()