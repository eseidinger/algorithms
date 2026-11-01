# Algorithm Lab

Ich habe dieses Repository erstellt, um nicht den Spaß am Programmieren zu verlieren. Ich benutze in letzter Zeit
sehr viel KI, um Projekte zu realisieren. Dabei fühle ich mich oft nur als Zuschauer, als Reviewer, der viel zu oft
nachfragen muss, wie etwas funktioniert.

Dabei lerne ich natürlich auch sehr viel, aber es ersetzt nicht das Glücksgefühl, wenn man selbst etwas
programmiert hat und dann zum ersten Mal sieht, dass es funktioniert.

Ich will hier nicht falsch verstanden werden. Ich habe sehr viele Interessen, und KI hilft mir nun, sie auch wirklich
alle verfolgen zu können. Sie hilft mir, den Überblick zu behalten und bei Kontextwechseln nicht den Faden zu verlieren.
Sie läuft auch in diesem Repository mit, auch während ich dies hier schreibe. Dinge, die ich schon hundertmal gemacht
habe, oder Dinge, bei denen man ohnehin nur ein kopiertes Template anpasst, lasse ich gerne von ihr erledigen.
Aber die wirklich interessanten Dinge möchte ich selbst umsetzen und KI höchstens als Assistenten nutzen, um im Flow zu
bleiben.

Jetzt will ich aber endlich dazu kommen, was ich eigentlich in diesem Repository tun will: Ich will mich mit Algorithmen
beschäftigen und kleine Use Cases dazu implementieren. Dabei will ich auch gute Software- und Data-Engineering-Praktiken
anwenden.

## Vorgehen

Ausgangspunkt ist immer ein Algorithmus, den ich zuerst in Python implementiere. Dabei soll auch eine gute
Testabdeckung entstehen. Da Algorithmen nicht um ihrer selbst willen interessant sind, sondern oft auf bestimmten Daten
operieren, will ich mir auch die Speicherung dieser Daten anschauen. Zu jedem Algorithmus soll es einen Use Case geben,
der sich als Webanwendung umsetzen lässt.

## Technologie-Stack

Jeder Use Case wird mit folgenden Technologien umgesetzt:

- **Python** für die Implementierung des Algorithmus samt Tests
- **FastAPI** für das Backend
- **TypeScript und React** für das Frontend

Je nach Anwendbarkeit kommen zusätzlich hinzu:

- **Spring und Kotlin** für Dienste, bei denen sich Java-Enterprise-Technologien anbieten
- **LangChain** für KI-Anwendungsfälle, wenn sich ein solcher Use Case anbietet

Da mich Java, Spring und andere Java-Enterprise-Technologien sehr geprägt haben und ich viel Erfahrung damit habe, will
ich sie an passender Stelle einsetzen. Dabei verwende ich die Kombination aus Spring und Kotlin, da Java, auch wenn es
sich in den letzten Jahren stark verbessert hat, immer noch sehr viel Boilerplate-Code erfordert. Kotlin ist da deutlich
angenehmer zu benutzen.

Was den Technologie-Stack angeht, gefällt mir diese Kombination sehr gut. Er ist modern und repräsentiert meine
Erfahrung aus Beruf, Studium und Fortbildung.

## Datenhaltung

Aus Data-Engineering-Sicht will ich von PostgreSQL ausgehen und mir dann anschauen, welche anderen Datenbanken und
Speichertechnologien sich für bestimmte Anwendungsfälle besser eignen. PostgreSQL soll dabei immer die Basis sein, da es
eine sehr gute Allround-Datenbank ist und durch die Unterstützung von JSON und JSONB auch NoSQL-ähnliche Anwendungsfälle
abdecken kann. Durch Erweiterungen kann es auch für Graph-, Time-Series- und Vektor-Datenbanken sowie weitere
Anwendungsfälle genutzt werden. Ich will mir aber auch andere Datenbanken anschauen, die sich für bestimmte
Anwendungsfälle besser eignen, und die Vor- und Nachteile der verschiedenen Datenbanken und Speichertechnologien
vergleichen und dokumentieren.

## Inspiration

Die maßgebliche Inspiration für dieses Repository kommt von vier Büchern, die ich in den letzten Jahren gelesen habe:

- "Algorithmen in Python" von David Kopec
- "Bioinformatics Algorithms" von Phillip Compeau und Pavel Pevzner
- "Designing Data-Intensive Applications" von Martin Kleppmann
- "Just Use Postgres!" von Denis Magda

Die ersten beiden Bücher haben mir noch einmal einen anderen Zugang zu Algorithmen gegeben. Die letzten beiden haben mir
gezeigt, dass man mit einer Standardlösung wie PostgreSQL sehr viele Anwendungsfälle abdecken kann, in welchen Fällen man
besser auf andere Datenbanken und Speichertechnologien zurückgreifen sollte und was bei deren Einsatz zu beachten ist.

## Lokale Entwicklung

Die englische Anleitung [Local Development, Builds, and Database Migrations](docs/development.md) beschreibt Einrichtung, Konfiguration, Prüfungen und Datenbankmigrationen.

## Architektur

Die englische [Architekturdokumentation](docs/architecture.md) beschreibt Komponenten, Datenverantwortung, API-Abläufe, Auftragsreservierungen und geplante Erweiterungen.
