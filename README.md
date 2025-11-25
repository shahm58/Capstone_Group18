pdf_processor/                       # 🔹 Root project folder (name can match repo name)
│
├── 📄 README.md                      # Overview, setup steps, and how to run the project
├── 📄 requirements.txt               # Python dependencies
├── 📄 .gitignore                     # Ignore data/output/temp files
├── 📄 main.py                        # Orchestrator (runs all modules together)
│
├── 📂 data/                          # All data lives here
│   ├── 📂 pdfs/                      # Raw input PDFs (manually dropped here)
│   ├── 📂 extracted/                 # Raw text & table extraction results
│   ├── 📂 cleaned/                   # Cleaned and structured data
│   ├── 📂 output/                    # Final combined datasets (CSV, JSON, or DB)
│   └── 📂 logs/                      # Logs for each run (optional)
│
├── 📂 core/                          # All main logic lives here
│   ├── 📄 loader.py                  # Scans /data/pdfs/ and lists files to process
│   ├── 📄 extractor.py               # Extracts text/tables from PDFs
│   ├── 📄 cleaner.py                 # Cleans and formats extracted data
│   ├── 📄 storage.py                 # Saves results to CSV/DB
│   ├── 📄 utils.py                   # Helper functions (logging, file ops, etc.)
│   └── 📄 ocr.py                     # Handles scanned PDFs (optional, OCR)
│   └── 📄 validator.py               # JSON Schema validator
│   └── 📄 metrics.py                 # Extracts ESG metrics (Scope 1 & 2)
│
├── 📂 config/                        # Configuration files and settings
│   ├── 📄 settings.yaml              # Paths, extraction options, etc.
│   └── 📄 schema.json                # (Optional) defines data structure/fields
│
├── 📂 docs/                          # For your reports, documentation, and diagrams
│   ├── 📄 design_overview.md         # System design doc
│   ├── 📄 roles_and_modules.md       # Who owns what part
│   └── 📄 flowchart.png              # Architecture or process diagram
│
├── 📂 tests/                         # Unit and integration tests
│   ├── 📄 test_extractor.py
│   ├── 📄 test_cleaner.py
│   └── 📄 test_storage.py
│
└── 📂 notebooks/                     # (Optional) Jupyter notebooks for exploration
    └── 📄 sample_analysis.ipynb
