import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime as date
import smtplib
from email.mime.text import MIMEText


if "role" not in st.session_state or st.session_state.role != "loja2":
    st.error("⚠️ Acesso negado!")
    st.stop()

#Função para enviar email
def enviar_email(destinatario, assunto, mensagem):
    remetente = st.secrets["email"]["remetente"]
    senha_app = st.secrets["email"]["senha"]

    msg = MIMEText(mensagem)
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = destinatario

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(remetente, senha_app)
        smtp.send_message(msg)

# --- CONFIGURAÇÃO---
gcp_info = st.secrets["gcp"]
planilha_chave = st.secrets["planilha"]["chave"]

# Criar credenciais
creds = Credentials.from_service_account_info(
    dict(gcp_info),
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)

# --- CONEXÃO COM GOOGLE SHEETS ---
cliente = gspread.authorize(creds)
planilha = cliente.open_by_key(planilha_chave)
aba = planilha.worksheet("iguatemi2")

def carregar_pedidos():
    dados = aba.get_all_records()
    return pd.DataFrame(dados)

planilha_Dados = carregar_pedidos()

hoje =  date.date.today().strftime("%d/%m/%Y")

planilha_Dados["Data Agendada"] = (
    pd.to_datetime(
        planilha_Dados["Data Agendada"],
        errors="coerce",
        dayfirst=True
    ).dt.strftime("%d/%m/%Y")
)

#---CONFIGURAÇÃO DE DATA---
agendamentos_hoje = planilha_Dados[planilha_Dados["Data Agendada"] == hoje]

# ---CONFIGURAÇÃO DE PAGINA---
st.set_page_config(" Painel de Agendamentos - Fibra",page_icon= "🌐" , layout="wide")

windows =st.sidebar.radio("Painéis",["Agendamentos - Fibra", "Acompanhamento Geral"])

if windows == "Agendamentos - Fibra":

    st.title("🌐 Painel de Agendamentos - Fibra")

    col1,col2,col3,col4 = st.columns(4)

    lojas_painel1 = ["LOJA IGUATEMI || BA"]

    #---APLICAÇÃO DE FILTROS---
    with col1:
        loja_filtro = st.selectbox("Loja",lojas_painel1,key="loja_fibra")

    with col2:
        nome_filtro = st.text_input("🔍 Buscar por consultor",key="nome_fibra")

    with col3:
        ordem_filtro = st.text_input("🔍 Buscar por SDR da fixa",key="ordem_fibra")

    with col4:
        data_filtro = st.date_input("🔍 Buscar por data",key="data_fibra")

    #---CONDIÇÕES DE FILTRO
    if loja_filtro:
        planilha_Dados = planilha_Dados[planilha_Dados["Loja"].str.contains(loja_filtro,case =False)]

    if nome_filtro:
        planilha_Dados = planilha_Dados[planilha_Dados["Consultor"].str.contains(nome_filtro,case =False)]

    if ordem_filtro:
        planilha_Dados = planilha_Dados[planilha_Dados["SDR FIXA"].str.contains(ordem_filtro,case =False)]

    if data_filtro:
        data_str = data_filtro.strftime("%d/%m/%Y")
        planilha_Dados = planilha_Dados[planilha_Dados["Data Agendada"] == data_str]

    status_opcoes = ["Concluído","Agendada","Pendente(Agendamento)","Pendente (Retenção)", "Cancelado"]

    #---STATUS DO AGENDAMENTO ---
    editado = st.data_editor(
        planilha_Dados,
        column_config={
            "Status da Fibra": st.column_config.SelectboxColumn(
                "Status da Fibra",
                options=status_opcoes,
                help="Selecione o status",
                required=True
            ),
            "Observação": st.column_config.TextColumn("Observação",
            required=False),
            "Data Agendada": st.column_config.TextColumn("Data Agendada",
            required=False),
            "Hora Agendada": st.column_config.TextColumn("Hora Agendada",
            required=False),
        },
        hide_index=True
    )

    colA, colB, colC = st.columns([1, 1, 6])
    # ====== Salvar alterações ======
    with colA:
        if st.button("Salvar alterações"):
            
            df_original = carregar_pedidos()

            st.success("Planilha atualizada!")

            for _, linha_editada in editado.iterrows():

                id_atual = linha_editada["SDR FIXA"]       # ID único
                novo_status = linha_editada["Status da Fibra"]         # novo valor

                # Procura a mesma linha na planilha original
                linha_original = df_original[df_original["SDR FIXA"] == id_atual]

                if linha_original.empty:
                    continue

                # Índice da linha dentro da planilha
                idx_sheet = linha_original.index[0] + 2  
                # +2 (linha 1 = cabeçalho, linha 2 = primeira linha de dados)
                # Descobre qual coluna é "Status"
                coluna_status = df_original.columns.get_loc("Status da Fibra") + 1
                
                coluna_obs = df_original.columns.get_loc("Observação") + 1

                coluna_data = df_original.columns.get_loc("Data Agendada") + 1 

                coluna_hora = df_original.columns.get_loc("Hora Agendada") + 1

                nova_observacao = linha_editada["Observação"]

                nova_data = linha_editada["Data Agendada"]

                nova_hora = linha_editada["Hora Agendada"]


                # Atualiza apenas o STATUS na célula certa
                aba.update_cell(idx_sheet, coluna_status, novo_status)
                aba.update_cell(idx_sheet, coluna_obs, nova_observacao)
                aba.update_cell(idx_sheet, coluna_data, nova_data)
                aba.update_cell(idx_sheet , coluna_hora , nova_hora)

    # ==== ENVIAR LEMBRETE NO EMAIL ====
    with colB:
        if st.button("📩 Enviar lembrete"):
            for _, linha in agendamentos_hoje.iterrows():

                email = linha["Email"]
                consultor = linha["Consultor"]
                ordem = linha["SDR FIXA"]
                data = linha["Data Agendada"]
                hora = linha["Hora Agendada"]
                status = linha["Status da Fibra"]
                mensagem = f"Assistente de Agendamento-Fibra \n\n Olá {consultor}, lembrete do seu agendamento de hoje! \n SDR FIXA: {ordem}\n Status da Fibra: {status} \n Data de agendamento: {data} \n Hora Agendada: {hora} \n Por gentileza, verifique o andamento da instalação ou informe a pessoa responsável por acompanhar os andamentos da fibra."
                enviar_email(email, "Lembrete de Agendamento", mensagem)

            st.success(f"Lembretes enviados para {len(agendamentos_hoje)} consultores.")


    # === ATUALIZAR A PLANIHA ====
    with colC:
        if st.button("🔄 Atualizar"):
            st.rerun()


    if len(agendamentos_hoje) != 0:
        st.warning(f"Tem agendamento para hoje: {len(agendamentos_hoje)}")

    else:
        st.warning("Não tem agendamento pra hoje")


if windows == "Acompanhamento Geral":

    st.title("🌐 Acompanhamento Geral - Fibra")

    col1,col2,col3,col4 = st.columns(4)

    lojas_painel2 = ["LOJA IGUATEMI || BA"]

    consultores = ["" ,"teste"]

    status_opcoes = ["","Concluído","Agendada","Pendente\(Agendamento\)","Pendente \(Retenção\)", "Cancelado"]

    #---APLICAÇÃO DE FILTROS---
    with col1:
        loja_filtro = st.selectbox("Loja",lojas_painel2,key="painel2")

    with col2:
        nome_filtro = st.selectbox("🔍 Buscar por consultor",consultores,key="nome_geral")

    with col3:
        ordem_filtro = st.text_input("🔍 Buscar por SDR da fixa,",key="ordem_geral")
    
    with col4:
        status_filtro = st.selectbox("🔍 Buscar por Status da Fibra",status_opcoes,key="status_geral")
    

    #---CONDIÇÕES DE FILTRO
    if loja_filtro:
        planilha_Dados = planilha_Dados[planilha_Dados["Loja"].str.contains(loja_filtro,case =False)]

    if nome_filtro:
        planilha_Dados = planilha_Dados[planilha_Dados["Consultor"].str.contains(nome_filtro,case =False)]

    if ordem_filtro:
        planilha_Dados = planilha_Dados[planilha_Dados["SDR FIXA"].str.contains(ordem_filtro,case =False)]
    
    if status_filtro:
        planilha_Dados = planilha_Dados[planilha_Dados["Status da Fibra"].str.contains(status_filtro,case =False)]
    


    st.dataframe(planilha_Dados)

    contagemT = planilha_Dados["Status da Fibra"].count()
    contagemA = planilha_Dados["Status da Fibra"].astype(str).str.contains("Agendada",case=False,na=False).sum()
    contagemC = planilha_Dados["Status da Fibra"].astype(str).str.contains("Cancelado",case=False,na=False).sum()
    contagemI = planilha_Dados["Status da Fibra"].astype(str).str.contains("Concluído",case=False,na=False).sum()
    contagemPA = planilha_Dados["Status da Fibra"].astype(str).str.contains("Pendente\(Agendamento\)",case=False,na=False).sum()
    contagemPr = planilha_Dados["Status da Fibra"].astype(str).str.contains("Pendente \(Retenção\)",case=False,na=False).sum()
    

    colf1,colf2,colf3,colf4,colf5,colf6 = st.columns(6)

    with colf1:
        st.text(f"🌐 Total de Fibras : {contagemT}")

    with colf2:
        st.text(f"🟡 Fibras agendadas : {contagemA}")

    with colf3:
        st.text(f"🟢 Fibras instaladas : {contagemI}")
    
    with colf4:
        st.text(f"🟡 Pendente(Agendamento) : {contagemPA}")
    
    with colf5:
            st.text(f"🟠 Pendente(Retenção) : {contagemPr}")

    with colf6:
        st.text(f"🔴 Fibras canceladas : {contagemC}")

    






