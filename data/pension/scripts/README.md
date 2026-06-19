# Pension · сценарии и справочники (не RAG)

```
data/pension/
├── book_complete (1).md     # книга
├── my_strategy.txt          # тон/стратегия (не RAG)
├── style_author.txt         # голос автора (не RAG)
├── scripts/
│   ├── _template_myachin_script.md
│   ├── myachin/             # эталоны Мячина (PDF, не индексируются)
│   └── pension_yt/          # ваши сценарии YT
└── reference/
    └── books/               # Марков, Талеб (не индексируются)
```

**RAG для постов Empire:** только `kb_sources/pension/` (Кримсон и др.).

```bash
./venv/bin/python tools/build_rag.py --persona pension --force --input-dir kb_sources/pension
```

См. `docs/EMPIRE_PIPELINE_CHECKLIST.md` · `docs/pension_reference_myachin.md`
