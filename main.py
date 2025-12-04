import streamlit as st

st.set_page_config(page_title="Login", page_icon="🔒")

usuarios = {
    "Iguatemi1": {"senha": "Iguatemi12026", "role": "loja1"},
    "Iguatemi2": {"senha": "Iguatemi22026", "role": "loja2"},
    "Admin":     {"senha": "admin2026",      "role": "admin"}
}

# Inicializar session_state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.role = None

def login():
    st.title("Login")

    user = st.text_input("Usuário:")
    password = st.text_input("Senha:", type="password")

    if st.button("Entrar"):
        if user in usuarios and password == usuarios[user]["senha"]:
            st.session_state.logged_in = True
            st.session_state.user = user
            st.session_state.role = usuarios[user]["role"]
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos!")

def logout():
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.role = None
    st.rerun()

# Roteamento
if not st.session_state.logged_in:
    login()
else:
    st.title(f"Bem-vindo, {st.session_state.user}")
    st.sidebar.button("Sair", on_click=logout)

    st.write("Use o menu à esquerda para acessar a página.")
