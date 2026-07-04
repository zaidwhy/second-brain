# Second Brain++ - Build Plan

> "Your Mind. Expanded." An AI-native knowledge OS that organizes, understands, connects, and evolves everything you learn - so knowledge finds you instead of you searching for it.

## What it is / why it matters

Second Brain++ turns the Personal LLM's memory into a **living knowledge graph**. It ingests your notes, PDFs, papers, and code, extracts concepts and relationships, and surfaces hidden connections you would otherwise forget. It is the difference between "AI that stores text" and "AI that thinks alongside you."

**Resume angle:** demonstrates ingestion pipelines, embeddings, and graph reasoning - the exact skills behind modern RAG and knowledge products. Highly demoable ("watch it connect a paper I read last year to today's project").

## Where it sits in the ecosystem

- **Depends on:** Personal LLM (#1) for the model router, memory, and RAG.
- **Provides to downstream:** the Knowledge Graph and ingestion layer used by DreamOS, Digital Twin, AI Scientist, InterviewOS, and Career Strategist.

## MVP scope (v0.1)

- Ingest **markdown and PDF** into chunks + embeddings.
- **Semantic search** over everything in natural language.
- **Auto-linking:** suggest related notes when you open or write one.
- A **basic knowledge-graph view** (nodes = notes/concepts, edges = relationships).

**Non-goals for v0.1:** the 18-integration list (Notion, Obsidian, Zotero, Readwise, YouTube, etc.), voice/visual search, spaced-repetition learning engine, idea-generation engine, predictive memory. Add integrations one at a time only after the core graph is solid.

## Phased roadmap

- **Prototype (S):** ingest markdown, embed, semantic search from the CLI.
- **MVP (M):** add PDF ingestion, entity/concept extraction, auto-linking, and a simple graph UI.
- **v1 (M):** connection-discovery notifications ("this contradicts an earlier note"), one external integration (Obsidian vault or Google Drive), timeline view.
- **Stretch (L):** learning engine (quizzes, spaced repetition), idea generator, predictive surfacing, more integrations.

## Tech stack

Reuse Personal LLM's core (router, RAG, memory). Add a graph store (Neo4j or a SQLite-backed graph), an ingestion queue, a PDF/text parser, and a graph-visualization frontend (Next.js + a force-graph library). Embeddings via the Anthropic API or a local embedding model.

## First tasks

1. Define the graph schema: node types (note, concept, person, project) and edge types.
2. Build the markdown ingestion pipeline into `packages/core` RAG + a new `graph` module.
3. Extract entities/concepts per chunk with an LLM call; write nodes and edges.
4. Ship semantic search over the ingested corpus.
5. Add auto-link suggestions: on note open, retrieve top related nodes and render them.

## Reference

Full north-star vision: `C:\Users\Asus\Documents\fable 5\second brain.txt`.
