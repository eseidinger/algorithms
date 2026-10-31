package de.eseidinger.algorithmlab.dataservice.catalog

import org.springframework.jdbc.core.simple.JdbcClient
import org.springframework.stereotype.Repository
import tools.jackson.databind.ObjectMapper
import java.util.UUID

@Repository
class CatalogRepository(
    private val jdbc: JdbcClient,
    private val objectMapper: ObjectMapper,
) {
    fun findAllShowcases(): List<Showcase> =
        jdbc
            .sql(
                """
                SELECT id, name, description
                FROM catalog.showcase
                ORDER BY id
                """.trimIndent(),
            ).query { row, _ ->
                Showcase(
                    id = row.getString("id"),
                    name = row.getString("name"),
                    description = row.getString("description"),
                )
            }.list()

    fun findScenarioVersion(id: UUID): ScenarioVersion? =
        jdbc
            .sql(
                """
                SELECT id, scenario_id, showcase_id, version, name, input
                FROM catalog.scenario_version
                WHERE id = :id
                """.trimIndent(),
            ).param("id", id)
            .query { row, _ ->
                ScenarioVersion(
                    id = row.getObject("id", UUID::class.java),
                    scenarioId = row.getObject("scenario_id", UUID::class.java),
                    showcaseId = row.getString("showcase_id"),
                    version = row.getInt("version"),
                    name = row.getString("name"),
                    input = objectMapper.readTree(row.getString("input")),
                )
            }.optional()
            .orElse(null)
}
