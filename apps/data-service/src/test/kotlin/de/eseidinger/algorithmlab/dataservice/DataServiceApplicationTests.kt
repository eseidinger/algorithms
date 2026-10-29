package de.eseidinger.algorithmlab.dataservice

import org.flywaydb.core.Flyway
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.testcontainers.service.connection.ServiceConnection
import org.springframework.jdbc.core.simple.JdbcClient
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers
import org.testcontainers.postgresql.PostgreSQLContainer
import kotlin.test.assertEquals
import kotlin.test.assertTrue

@Testcontainers
@SpringBootTest
class DataServiceApplicationTests {
    @Autowired
    private lateinit var jdbc: JdbcClient

    @Autowired
    private lateinit var flyway: Flyway

    @Test
    fun `migration seeds the Fibonacci showcase in the catalog schema`() {
        val name =
            jdbc
                .sql("SELECT name FROM catalog.showcase WHERE id = 'K01'")
                .query(String::class.java)
                .single()

        assertEquals("Fibonacci", name)
        assertEquals(
            "1",
            flyway
                .info()
                .current()
                .version.version,
        )
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
