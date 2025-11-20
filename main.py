import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime as date
import smtplib
from email.mime.text import MIMEText

#Função para enviar email
def enviar_email(destinatario, assunto, mensagem):
    remetente = "victorritossantos@gmail.com"
    senha_app = "tqpb nefl vxxc uqsk"

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
aba = planilha.sheet1

def carregar_pedidos():
    dados = aba.get_all_records()
    return pd.DataFrame(dados)

planilha_Dados = carregar_pedidos()

hoje =  date.date.today().strftime("%d/%m/%Y")

planilha_Dados["Data Agendada"] = pd.to_datetime(planilha_Dados["Data Agendada"]).dt.strftime("%d/%m/%Y")

agendamentos_hoje = planilha_Dados[planilha_Dados["Data Agendada"] == hoje]

# ---CONFIGURAÇÃO DE PAGINA---
st.set_page_config(" Painel de Agendamentos - Fibra",page_icon= "🌐" , layout="wide")

st.title("🌐 Painel de Agendamentos - Fibra")

col1,col2,col3,col4 = st.columns(4)

lojas = [" ","LOJA IGUATEMI | BA" , "LOJA IGUATEMI || BA"]

#---APLICAÇÃO DE FILTROS---
with col1:
    loja_filtro = st.selectbox("🔍 Buscar por loja",lojas)

with col2:
    nome_filtro = st.text_input("🔍 Buscar por consultor")

with col3:
    ordem_filtro = st.text_input("🔍 Buscar por N° ordem")

with col4:
    data_filtro = st.date_input("🔍 Buscar por data")


if loja_filtro:
    planilha_Dados = planilha_Dados[planilha_Dados["Loja"].str.contains(loja_filtro,case =False)]

if nome_filtro:
    planilha_Dados = planilha_Dados[planilha_Dados["Consultor"].str.contains(nome_filtro,case =False)]

if ordem_filtro:
    planilha_Dados = planilha_Dados[planilha_Dados["N° da Ordem"].str.contains(ordem_filtro,case =False)]

if data_filtro:
    data_str = data_filtro.strftime("%d/%m/%Y")
    planilha_Dados = planilha_Dados[planilha_Dados["Data Agendada"] == data_str]

status_opcoes = ["Pendente(Agendamento)","Pendente (Retenção)","Concluído", "Cancelado"]

#---STATUS DO AGENDAMENTO ---
editado = st.data_editor(
    planilha_Dados,
    column_config={
        "Status da Fibra": st.column_config.SelectboxColumn(
            "Status da Fibra",
            options=status_opcoes,
            help="Selecione o status",
            required=True
        )
    },
    hide_index=True
)

colA, colB, colC = st.columns([1, 1, 6])
# ====== Salvar alterações ======
with colA:
    if st.button("Salvar alterações"):
         df_original = carregar_pedidos()

         for _, linha_editada in editado.iterrows():

                id_atual = linha_editada["N° da Ordem"]       # ID único
                novo_status = linha_editada["Status da Fibra"]         # novo valor

                # Procura a mesma linha na planilha original
                linha_original = df_original[df_original["N° da Ordem"] == id_atual]

                if linha_original.empty:
                    continue

                # Índice da linha dentro da planilha
                idx_sheet = linha_original.index[0] + 2  
                # +2 (linha 1 = cabeçalho, linha 2 = primeira linha de dados)
                # Descobre qual coluna é "Status"
                coluna_status = df_original.columns.get_loc("Status") + 1

                # Atualiza apenas o STATUS na célula certa
                aba.update_cell(idx_sheet, coluna_status, novo_status)

                st.success("Planilha atualizada!")

with colB:
    if st.button("Enviar lembrete"):
        for _, linha in agendamentos_hoje.iterrows():

            email = linha["Email"]
            consultor = linha["Consultor"]
            ordem = linha["N° da Ordem"]
            data = linha["Data Agendada"]
            hora = linha["Hora Agendada"]
            mensagem = f"Assistente de Agendamento-Fibra \n\n Olá {consultor}, lembrete do seu agendamento de hoje! \n N° da ordem: {ordem} \n Data de agendamento: {data} \n Hora Agendada {hora} \n por gentileza verificar o andamento da instalação ou informar a pessoa responsavel por visualizar dos andamentos da fibra"
            enviar_email(email, "Lembrete de Agendamento", mensagem)

        st.success(f"Lembretes enviados para {len(agendamentos_hoje)} consultores.")


with colC:
    if st.button("🔄 Atualizar"):
        st.rerun()


if len(agendamentos_hoje) != 0:
    st.warning(f"Tem agendamento para hoje: {len(agendamentos_hoje)}")

else:
    st.warning("Não tem agendamento pra hoje")
