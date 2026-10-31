package de.eseidinger.algorithmlab.dataservice.catalog

import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController
import java.util.UUID

@RestController
@RequestMapping("/api/data")
class CatalogController(
    private val repository: CatalogRepository,
) {
    @GetMapping("/showcases")
    fun listShowcases(): List<Showcase> = repository.findAllShowcases()

    @GetMapping("/scenario-versions/{id}")
    fun getScenarioVersion(
        @PathVariable id: UUID,
    ): ResponseEntity<ScenarioVersion> = ResponseEntity.ofNullable(repository.findScenarioVersion(id))
}
