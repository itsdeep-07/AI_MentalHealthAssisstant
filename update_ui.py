import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. State initialization
state_init = """if "last_event_id" not in st.session_state: st.session_state.last_event_id = None
if "show_stats" not in st.session_state: st.session_state.show_stats = False
if "completed_tasks" not in st.session_state: st.session_state.completed_tasks = set()"""

content = re.sub(r'if "last_event_id" not in st\.session_state: st\.session_state\.last_event_id = None', state_init, content)

# 2. Background extraction and injection
bg_pattern = r"st\.markdown\('''(.*?)<div style=\"position:fixed; inset:0; z-index:-1; width:100vw; height:100vh; background-image:url\((.*?)\); background-size:cover; background-position:center; filter:brightness\(0\.4\);\"></div>(.*?''', unsafe_allow_html=True\))"
bg_match = re.search(bg_pattern, content, re.DOTALL)
if bg_match:
    bg_url = bg_match.group(2)
    # Remove from old place
    content = content.replace(f'<div style="position:fixed; inset:0; z-index:-1; width:100vw; height:100vh; background-image:url({bg_url}); background-size:cover; background-position:center; filter:brightness(0.4);"></div>', '')
    
    # Add CSS for animation
    css_anim = """
@keyframes bg-pan {
    0% { background-position: 0% 50%; filter:brightness(0.3); }
    50% { background-position: 100% 50%; filter:brightness(0.7); }
    100% { background-position: 0% 50%; filter:brightness(0.3); }
}
.dynamic-bg {
    position: fixed; inset: 0; z-index: -1; width: 100vw; height: 100vh;
    background-size: 150% 150%;
    animation: bg-pan 30s ease infinite;
}
"""
    content = content.replace('.animate-slow-pulse { animation: slow-pulse 3s infinite ease-in-out; }', '.animate-slow-pulse { animation: slow-pulse 3s infinite ease-in-out; }\n' + css_anim)
    
    # Insert Global background
    global_bg = f'''
# Global Dynamic Background
st.markdown(\'\'\'
<div class="dynamic-bg" style="background-image:url({bg_url});"></div>
\'\'\', unsafe_allow_html=True)

# Login Screen'''
    content = content.replace("# Login Screen (Custom styled inside streamlit)", global_bg)

# 3. Main Layout Adjustment
content = content.replace("col1, col2 = st.columns([1, 20])", "if st.session_state.show_stats:\n            col1, col2, col3 = st.columns([1, 15, 6])\n        else:\n            col1, col2 = st.columns([1, 20])\n            col3 = None")
content = content.replace("with col2:", "with col2:") # just anchor

# Replace the sidebar markdown with putting it into col3
sidebar_code = "if st.session_state.show_stats:\n                with st.sidebar:\n                    st.markdown(metrics_html, unsafe_allow_html=True)"
new_sidebar_code = "if st.session_state.show_stats and col3 is not None:\n                with col3:\n                    st.markdown(metrics_html, unsafe_allow_html=True)"
content = content.replace(sidebar_code, new_sidebar_code)
content = content.replace("st.sidebar.markdown(metrics_html, unsafe_allow_html=True)", "if col3: col3.markdown(metrics_html, unsafe_allow_html=True)")


# 4. Intervention Tasks Logic
task_btn_old = """if st.button("✓ " + msg):
                    log_intervention(st.session_state.user_id, time.time() - st.session_state.session_start_time, t_type, "Completed")
                    st.success("Log updated")"""
                    
task_btn_new = """task_id = "task_" + str(hash(msg + str(st.session_state.session_start_time)))
                if task_id in st.session_state.completed_tasks:
                    st.markdown(f'<div style="background:var(--bg-sparkline); padding:10px; border-radius:6px; color:var(--accent); text-align:center;">✅ <s>{msg}</s></div>', unsafe_allow_html=True)
                else:
                    if st.button("✓ " + msg, key=task_id):
                        st.session_state.completed_tasks.add(task_id)
                        log_intervention(st.session_state.user_id, time.time() - st.session_state.session_start_time, t_type, "Completed")
                        st.rerun()"""
content = content.replace(task_btn_old, task_btn_new)


with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("UI enhancements applied successfully.")
