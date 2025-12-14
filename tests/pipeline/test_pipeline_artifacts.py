from pptx_generator.pipeline.base import (
    PipelineArtifactKey,
    PipelineArtifacts,
)


def test_pipeline_artifacts_allows_enum_and_str_access() -> None:
    artifacts = PipelineArtifacts()
    artifacts[PipelineArtifactKey.GENERATE_READY_PATH] = "ready.json"
    artifacts["custom"] = 1

    assert artifacts[PipelineArtifactKey.GENERATE_READY_PATH] == "ready.json"
    assert artifacts["custom"] == 1
    assert artifacts.get(PipelineArtifactKey.GENERATE_READY_PATH) == "ready.json"


def test_pipeline_artifacts_as_dict_and_update() -> None:
    artifacts = PipelineArtifacts({"a": 1})
    artifacts.update({"b": 2})
    artifacts.setdefault("c", 3)

    snapshot = artifacts.as_dict()
    assert snapshot == {"a": 1, "b": 2, "c": 3}
    # __iter__ returns keys, so dict(artifacts.items()) is safe
    assert dict(artifacts.items()) == snapshot
