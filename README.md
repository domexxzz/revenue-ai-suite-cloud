# AI Business Prototype

Prototype dashboard สำหรับเดโม AI for Business ที่เน้น
- Deep customer analysis
- Real-time marketing recommendations
- AI content suggestions
- Branch/staff performance view

## Run

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run app.py
```

## Notes
- ใช้ข้อมูล mock เพื่อเดโม flow Data -> Insight -> Action
- สามารถเปลี่ยนเป็นข้อมูลจริงจาก POS ได้ในไฟล์ `data/sample_transactions.csv`
