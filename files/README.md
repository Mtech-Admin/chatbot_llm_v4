# DMRC HR Compendium — Structured Knowledge Base
### Generated from: Updated_HR_Compendium_NOV23.pdf (356 pages, 13 Chapters A–M)

---

## Files in this Package

| File | Purpose |
|------|---------|
| `dmrc_hr_knowledge_base.json` | Complete structured KB — chapters, rules, tables, indexes |
| `dmrc_hr_chunks.json` | 124 RAG-ready chunks ready for vector embedding |
| `README.md` | This file — integration guide |

---

## Knowledge Base Stats

| Metric | Count |
|--------|-------|
| Chapters | 13 (A through M) |
| Rules extracted | 65 |
| Tables (structured JSON) | 15 |
| Office Orders indexed | 46 |
| Cross-references mapped | 34 |
| Authority index entries | 26 |
| Leave types indexed | 13 |
| Financial limits indexed | 12 |
| **Total RAG chunks** | **124** |

---

## Chunk Types and When They Fire

| Chunk Type | Count | Best For Query Type |
|------------|-------|---------------------|
| `rule` | 65 | Specific rule lookup, eligibility, procedure |
| `chapter_summary` | 13 | "What does chapter X cover?", overview |
| `chapter_authority` | 13 | "Who approves X?", sanction authority |
| `cross_reference` | 13 | Multi-chapter queries |
| `table` | 15 | Rates, amounts, entitlements, calculations |
| `leave_types_index` | 1 | "How many types of leave?", list all leave |
| `document_summary` | 1 | "What chapters are in this document?" |
| `authority_index` | 1 | Global approval authority lookup |
| `oo_index` | 1 | Office order / circular reference queries |
| `financial_limits_index` | 1 | "What is the HBA limit?", all amounts |

---

## How to Ingest into a Vector Database

```python
import json
from openai import OpenAI  # or any embedding provider

client = OpenAI()

with open("dmrc_hr_chunks.json") as f:
    data = json.load(f)

chunks = data["chunks"]

# Embed each chunk
for chunk in chunks:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=chunk["content"]
    )
    chunk["embedding"] = response.data[0].embedding
    # Store chunk_id, content, embedding, metadata in your vector DB
    # e.g. Pinecone, Weaviate, pgvector
```

---

## Query Routing Logic

Before hitting the vector DB, classify the user's question:

```python
QUERY_ROUTING = {
    # Listing / counting → go to dedicated index chunks first
    "listing":    ["leave_types_index", "financial_limits_index", "chapter_summary"],
    
    # Specific rule lookup → rule chunks
    "specific":   ["rule", "table"],
    
    # Who approves → authority chunks
    "authority":  ["authority_index", "chapter_authority", "rule"],
    
    # Rate / amount / how much → table + financial index
    "rate":       ["table", "financial_limits_index", "rule"],
    
    # Cross-chapter / edge case → cross_reference + rule
    "complex":    ["cross_reference", "rule", "chapter_summary"],
    
    # Cite the rule / OO number → OO index
    "citation":   ["oo_index", "rule"],
    
    # Overview / what is in a chapter → chapter_summary
    "overview":   ["chapter_summary", "document_summary"],
}
```

---

## Answering "How many types of leave are there?"

This was the original problem. The solution is built in.

The chunk `DMRC-0002` has `chunk_type: "leave_types_index"` with:
- `count: 13`  
- A complete `summary_for_chatbot` paragraph listing all 13 types  
- Individual type entries with rule references  

When the query classifier detects a "listing/counting" intent, route directly to this chunk.
The LLM then answers: **"DMRC provides 13 types of leave..."** — correctly and completely.

---

## All 9 Query Scenario Solutions

| Scenario | Solution in This KB |
|----------|---------------------|
| Listing / counting | Dedicated index chunks (leave_types_index, financial_limits_index) |
| Eligibility queries | Rule chunks with `applies_to` and `eligibility_conditions` fields |
| Calculation / amounts | Table chunks + financial_limits_index |
| Procedure / how-to | Rule chunks with numbered key_points |
| Comparison | Multi-chunk retrieval: fetch both rule chunks and compare |
| Authority / approval | authority_index + chapter_authority chunks |
| Cross-chapter | cross_reference chunks + rule chunks across chapters |
| Rule citation | oo_index chunk + office_orders field in each rule |
| Conditional / edge case | Rule content includes exception clauses + cross_references |

---

## Metadata Fields on Every Chunk

```json
{
  "chunk_id": "DMRC-0045",
  "chunk_type": "rule",
  "chapter": "F",
  "chapter_title": "Leave Rules",
  "title": "Rule F.3.10: Maternity Leave",
  "content": "...",
  "metadata": {
    "rule_id": "F.3.10",
    "applies_to": ["female regular employees", "deputationists"],
    "approval_authority": "Competent Authority / HOD",
    "amounts_or_limits": "182 days (≤2 children); 12 weeks (>2); 45 days (miscarriage)",
    "office_orders": ["O.O. No. HR/O&M-140/2022", "O.O. No. PP/820/2008"],
    "page_range": "165-186",
    "query_types": ["specific rule", "eligibility", "procedure", "amount"]
  }
}
```

Use `metadata.query_types` to pre-filter chunks before vector search for faster, more accurate retrieval.

---

## Recommended System Prompt for Your Chatbot

```
You are an HR Policy Assistant for Delhi Metro Rail Corporation (DMRC).
Answer questions based ONLY on the DMRC HR Compendium (November 2023 edition).
Rules:
1. If the answer is in the provided context, answer accurately and cite the rule number and page.
2. If you are unsure or the information is not in the context, say "This is not covered in the provided HR Compendium sections — please contact HR."
3. For listing queries (e.g. "types of leave"), always give a complete numbered list.
4. For eligibility queries, always mention any conditions or exceptions.
5. For amounts and limits, always mention if the figure is subject to revision.
6. Always end your answer with: "Reference: [Rule X.X, Chapter X, Page XX]"
```

---

## Chapter Reference

| Chapter | Title | Pages |
|---------|-------|-------|
| A | General Conditions of Service Rules | 1-48 |
| B | Conduct, Discipline and Appeal Rules | 49-85 |
| C | Pay and Allowances Rules | 86-119 |
| D | Travelling Allowance / Daily Allowance Rules | 120-134 |
| E | Medical Attendance Rules | 135-164 |
| F | Leave Rules | 165-186 |
| G | House Building Advance Rules | 187-276 |
| H | Recruitment Rules | 277-288 |
| I | Vehicle Advance Rules | 289-299 |
| J | Multi-Purpose Advance Rules | 300-310 |
| K | Housing Allotment Rules | 311-328 |
| L | Staff Welfare Fund Rules | 329-340 |
| M | Leave Travel Concession Rules | 341-352 |
