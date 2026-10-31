package de.eseidinger.algorithmlab.dataservice.catalog

import tools.jackson.databind.JsonNode
import java.util.UUID

data class ScenarioVersion(
    val id: UUID,
    val scenarioId: UUID,
    val showcaseId: String,
    val version: Int,
    val name: String,
    val input: JsonNode,
)
