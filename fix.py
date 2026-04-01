import re
with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()
text = re.sub(r"st\.markdown\('\s*<div style=\"position:fixed; inset:0;", "st.markdown('''\\n<div style=\"position:fixed; inset:0;", text)
text = re.sub(r"Elevating Mental Clarity</p>\s*</div>\s*', unsafe_allow_html=True\)", "Elevating Mental Clarity</p>\\n</div>\\n''', unsafe_allow_html=True)", text)
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Syntax error fixed.")
