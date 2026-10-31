package de.eseidinger.algorithmlab.dataservice

import org.flywaydb.core.Flyway
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.testcontainers.service.connection.ServiceConnection
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc
import org.springframework.dao.DataAccessException
import org.springframework.http.MediaType
import org.springframework.jdbc.core.simple.JdbcClient
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.content
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.status
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers
import org.testcontainers.postgresql.PostgreSQLContainer
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

@Testcontainers
@SpringBootTest
@AutoConfigureMockMvc
class DataServiceApplicationTests {
    @Autowired
    private lateinit var mockMvc: MockMvc

    @Autowired
    private lateinit var jdbc: JdbcClient

    @Autowired
    private lateinit var flyway: Flyway

    @Test
    fun `catalog endpoint returns the Fibonacci showcase`() {
        mockMvc
            .perform(get("/api/data/showcases"))
            .andExpect(status().isOk)
            .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
            .andExpect(jsonPath("$[0].id").value("K01"))
            .andExpect(jsonPath("$[0].name").value("Fibonacci"))
    }

    @Test
    fun `scenario endpoint returns version metadata and structured input`() {
        val id = "00000000-0000-4000-8000-000000000010"
        mockMvc
            .perform(get("/api/data/scenario-versions/{id}", id))
            .andExpect(status().isOk)
            .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
            .andExpect(jsonPath("$.id").value(id))
            .andExpect(jsonPath("$.scenarioId").value("00000000-0000-4000-8000-000000000001"))
            .andExpect(jsonPath("$.showcaseId").value("K01"))
            .andExpect(jsonPath("$.version").value(1))
            .andExpect(jsonPath("$.name").value("Fibonacci with n = 10"))
            .andExpect(jsonPath("$.input").isMap)
            .andExpect(jsonPath("$.input.n").value(10))
    }

    @Test
    fun `unknown scenario version returns not found`() {
        mockMvc
            .perform(
                get("/api/data/scenario-versions/{id}", "00000000-0000-4000-8000-000000000099"),
            ).andExpect(status().isNotFound)
    }

    @Test
    fun `malformed scenario version ID returns bad request`() {
        mockMvc
            .perform(get("/api/data/scenario-versions/invalid"))
            .andExpect(status().isBadRequest)
    }

    @Test
    fun `migration seeds the Fibonacci showcase in the catalog schema`() {
        val name =
            jdbc
                .sql("SELECT name FROM catalog.showcase WHERE id = 'K01'")
                .query(String::class.java)
                .single()

        assertEquals("Fibonacci", name)
        assertTrue(flyway.validateWithResult().validationSuccessful)
    }

    @Test
    fun `applying migrations again does not duplicate the catalog entry`() {
        assertEquals(0, flyway.migrate().migrationsExecuted)
        val count =
            jdbc
                .sql("SELECT count(*) FROM catalog.showcase WHERE id = 'K01'")
                .query(Long::class.javaObjectType)
                .single()
        assertEquals(1L, count)
    }

    @Test
    fun `migration seeds the Fibonacci scenario input`() {
        val n =
            jdbc
                .sql(
                    """
                    SELECT (input ->> 'n')::integer
                    FROM catalog.scenario_version
                    WHERE id = '00000000-0000-4000-8000-000000000010'
                        AND showcase_id = 'K01'
                    """.trimIndent(),
                ).query(Int::class.javaObjectType)
                .single()

        assertEquals(10, n)
    }

    @Test
    fun `scenario versions cannot be changed`() {
        assertFailsWith<DataAccessException> {
            jdbc
                .sql(
                    """
                    UPDATE catalog.scenario_version
                    SET input = '{"n": 20}'
                    WHERE id = '00000000-0000-4000-8000-000000000010'
                    """.trimIndent(),
                ).update()
        }
    }

    companion object {
        @Container
        @ServiceConnection
        @JvmStatic
        val postgres =
            PostgreSQLContainer("postgres:18")
                .withDatabaseName("algorithm_lab_test")
                .withInitScript("db/test-init.sql")
    }
}
