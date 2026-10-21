"""Pydantic models for the scenario domain. Shapes mirror packages/schemas."""

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    """Base for all API-facing models: camelCase JSON, strict extra rejection."""

    model_config = ConfigDict(
        alias_generator=lambda name: "".join(
            part if i == 0 else part.capitalize() for i, part in enumerate(name.split("_"))
        ),
        populate_by_name=True,
        extra="forbid",
    )


class ScenarioStage(ContractModel):
    id: str
    name: str
    description: str
    weight: float = Field(ge=0, le=1)


class ScenarioEnvironment(ContractModel):
    organization: str
    compromised_identity: str
    note: str


class Scenario(ContractModel):
    id: str
    name: str
    description: str
    version: str
    seed: int
    synthetic_only: bool
    environment: ScenarioEnvironment
    stages: list[ScenarioStage]

    def stage(self, stage_id: str) -> ScenarioStage:
        for stage in self.stages:
            if stage.id == stage_id:
                return stage
        raise KeyError(f"unknown stage: {stage_id}")