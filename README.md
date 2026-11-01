# Algorithm Lab

I created this repository so I wouldn't lose the joy of programming. Lately I have been using AI a lot to realize
projects. In doing so, I often feel like a mere spectator, a reviewer who has to ask far too often how something works.

Of course, I also learn a lot that way, but it doesn't replace the happiness of programming something yourself and
seeing it work for the first time.

Don't get me wrong. I have a great many interests, and AI now helps me to actually pursue all of them. It helps me keep
track of things and not lose the thread when switching contexts. It also runs alongside me in this repository, even
while I write this. Things I have done a hundred times before, or things where you just adapt a copied template, I am
happy to let it handle. But the truly interesting things I want to build myself, using AI at most as an assistant to
stay in the flow.

Now I finally want to get to what I actually want to do in this repository: I want to explore algorithms and implement
small use cases for them. In the process, I also want to apply good software and data engineering practices.

## Approach

The starting point is always an algorithm, which I implement in Python first. Good test coverage should come out of
this as well. Since algorithms are not interesting for their own sake but often operate on specific data, I also want to
look at how that data is stored. Each algorithm should have a use case that can be implemented as a web application.

## Technology Stack

Every use case is implemented with the following technologies:

- **Python** for implementing the algorithm, including tests
- **FastAPI** for the backend
- **TypeScript and React** for the frontend

Depending on applicability, the following are added:

- **Spring and Kotlin** for services where Java enterprise technologies are a good fit
- **LangChain** for AI use cases, when one presents itself

Java, Spring and other Java enterprise technologies have shaped me greatly, and I have a lot of experience with them, so
I want to use them where appropriate. I use the combination of Spring and Kotlin, since Java, even though it has improved
a lot in recent years, still requires a great deal of boilerplate code. Kotlin is much more pleasant to use.

As far as the technology stack is concerned, I like this combination a lot. It is modern and represents my experience
from work, university and continuing education.

## Data Storage

From a data engineering perspective, I want to start with PostgreSQL and then look at which other databases and storage
technologies are better suited for certain use cases. PostgreSQL should always be the foundation, as it is a very good
all-round database and, thanks to its support for JSON and JSONB, can also cover NoSQL-like use cases. With extensions
it can also be used for graph, time-series and vector databases as well as other use cases. But I also want to look at
other databases that are better suited for particular use cases, and compare and document the pros and cons of the
different databases and storage technologies.

## Inspiration

The main inspiration for this repository comes from four books I have read over the past few years:

- "Algorithmen in Python" (Classic Computer Science Problems in Python) by David Kopec
- "Bioinformatics Algorithms" by Phillip Compeau and Pavel Pevzner
- "Designing Data-Intensive Applications" by Martin Kleppmann
- "Just Use Postgres!" by Denis Magda

The first two books gave me yet another way into algorithms. The last two showed me that a standard solution like
PostgreSQL can cover a great many use cases, in which cases it is better to turn to other databases and storage
technologies, and what to keep in mind when using them.

## Local Development

See [Local Development, Builds, and Database Migrations](docs/development.md) for setup, configuration, checks, and database lifecycle commands.

## Architecture

See [Architecture](docs/architecture.md) for component boundaries, data ownership, API flows, execution leases, and planned extensions.
