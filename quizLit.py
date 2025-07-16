"""
Quiz TGE APP 2025 - Versão Streamlit
Sistema de quiz com interface web usando Streamlit e SQLite
"""

import sqlite3
import random
import streamlit as st
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import os


# --------------------- Configurações ---------------------
class Config:
    """Configurações globais da aplicação"""
    # Proporções de questões
    SPECIFIC_QUESTIONS_RATIO = 0.6
    
    # Percentuais de desempenho
    EXCELLENT_THRESHOLD = 70
    GOOD_THRESHOLD = 50


class DatabasePath:
    """Caminhos dos bancos de dados"""
    SPECIFIC_QUESTIONS = 'questoesEspecificas.db'
    GENERAL_QUESTIONS = 'questoesGerais.db'


# --------------------- Modelos de Dados ---------------------
@dataclass
class Question:
    """Representa uma questão do quiz"""
    id: int
    numero: int
    enunciado: str
    alternativa_a: str
    alternativa_b: str
    alternativa_c: str
    alternativa_d: str
    fonte: str
    gabarito: str
    
    def get_alternatives(self) -> dict:
        """Retorna um dicionário com as alternativas"""
        return {
            'a': self.alternativa_a,
            'b': self.alternativa_b,
            'c': self.alternativa_c,
            'd': self.alternativa_d
        }


class PerformanceLevel(Enum):
    """Níveis de desempenho do usuário"""
    EXCELLENT = "excellent"
    GOOD = "good"
    NEEDS_IMPROVEMENT = "needs_improvement"


# --------------------- Gerenciador de Dados ---------------------
class DatabaseManager:
    """Gerencia operações com banco de dados"""
    
    @staticmethod
    def load_questions(database_path: str) -> List[Question]:
        """Carrega questões do banco de dados"""
        if not os.path.exists(database_path):
            st.error(f"Banco de dados não encontrado: {database_path}")
            return []
        
        try:
            conn = sqlite3.connect(database_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, numero, enunciado, alternativa_a, alternativa_b, 
                       alternativa_c, alternativa_d, fonte, gabarito 
                FROM questoes
            ''')
            rows = cursor.fetchall()
            conn.close()
            
            return [Question(*row) for row in rows]
        except sqlite3.Error as e:
            st.error(f"Erro ao carregar questões: {e}")
            return []


class QuestionManager:
    """Gerencia a seleção e preparação das questões"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def prepare_questions(self, total_questions: int) -> List[Question]:
        """Prepara questões misturadas de ambos os bancos"""
        specific_questions = self.db_manager.load_questions(DatabasePath.SPECIFIC_QUESTIONS)
        general_questions = self.db_manager.load_questions(DatabasePath.GENERAL_QUESTIONS)
        
        if not specific_questions and not general_questions:
            st.error("Nenhuma questão encontrada nos bancos de dados!")
            return []
        
        # Usar apenas as questões disponíveis se um banco não existir
        available_questions = []
        if specific_questions:
            random.shuffle(specific_questions)
            num_specific = int(total_questions * Config.SPECIFIC_QUESTIONS_RATIO)
            available_questions.extend(specific_questions[:num_specific])
        
        if general_questions:
            random.shuffle(general_questions)
            num_general = total_questions - len(available_questions)
            if num_general > 0:
                available_questions.extend(general_questions[:num_general])
        
        # Se ainda não temos questões suficientes, usar todas disponíveis
        if len(available_questions) < total_questions:
            all_questions = specific_questions + general_questions
            random.shuffle(all_questions)
            available_questions = all_questions[:total_questions]
        
        random.shuffle(available_questions)
        return available_questions


class PerformanceEvaluator:
    """Avalia o desempenho do usuário"""
    
    @staticmethod
    def evaluate_performance(correct_answers: int, total_questions: int) -> Tuple[float, PerformanceLevel, str]:
        """Avalia o desempenho e retorna percentual, nível e mensagem"""
        if total_questions == 0:
            return 0.0, PerformanceLevel.NEEDS_IMPROVEMENT, "Nenhuma questão respondida"
        
        percentage = (correct_answers / total_questions) * 100
        
        if percentage >= Config.EXCELLENT_THRESHOLD:
            level = PerformanceLevel.EXCELLENT
            message = "🎉 Parabéns! Excelente desempenho!"
        elif percentage >= Config.GOOD_THRESHOLD:
            level = PerformanceLevel.GOOD
            message = "👍 Bom trabalho! Continue estudando!"
        else:
            level = PerformanceLevel.NEEDS_IMPROVEMENT
            message = "📚 Continue estudando para melhorar!"
        
        return percentage, level, message


# --------------------- Aplicação Streamlit ---------------------
def initialize_session_state():
    """Inicializa o estado da sessão"""
    if 'quiz_started' not in st.session_state:
        st.session_state.quiz_started = False
    if 'questions' not in st.session_state:
        st.session_state.questions = []
    if 'current_question' not in st.session_state:
        st.session_state.current_question = 0
    if 'correct_answers' not in st.session_state:
        st.session_state.correct_answers = 0
    if 'user_answers' not in st.session_state:
        st.session_state.user_answers = []
    if 'quiz_finished' not in st.session_state:
        st.session_state.quiz_finished = False
    if 'show_result' not in st.session_state:
        st.session_state.show_result = False
    if 'last_answer_correct' not in st.session_state:
        st.session_state.last_answer_correct = None


def reset_quiz():
    """Reseta o estado do quiz"""
    st.session_state.quiz_started = False
    st.session_state.questions = []
    st.session_state.current_question = 0
    st.session_state.correct_answers = 0
    st.session_state.user_answers = []
    st.session_state.quiz_finished = False
    st.session_state.show_result = False
    st.session_state.last_answer_correct = None


def start_quiz(total_questions: int):
    """Inicia o quiz"""
    question_manager = QuestionManager()
    questions = question_manager.prepare_questions(total_questions)
    
    if not questions:
        st.error("Não foi possível carregar as questões. Verifique se os bancos de dados estão disponíveis.")
        return
    
    st.session_state.questions = questions
    st.session_state.quiz_started = True
    st.session_state.current_question = 0
    st.session_state.correct_answers = 0
    st.session_state.user_answers = []
    st.session_state.quiz_finished = False
    st.session_state.show_result = False


def answer_question(selected_answer: str):
    """Processa a resposta do usuário"""
    if st.session_state.quiz_finished:
        return
    
    current_q = st.session_state.questions[st.session_state.current_question]
    is_correct = selected_answer == current_q.gabarito
    
    if is_correct:
        st.session_state.correct_answers += 1
    
    st.session_state.user_answers.append({
        'question': current_q,
        'user_answer': selected_answer,
        'correct_answer': current_q.gabarito,
        'is_correct': is_correct
    })
    
    st.session_state.last_answer_correct = is_correct
    st.session_state.show_result = True


def next_question():
    """Avança para a próxima questão"""
    st.session_state.current_question += 1
    st.session_state.show_result = False
    st.session_state.last_answer_correct = None
    
    if st.session_state.current_question >= len(st.session_state.questions):
        st.session_state.quiz_finished = True


def show_initial_screen():
    """Mostra a tela inicial"""
    st.title("🎓 Quiz TGE APP 2025")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Configuração do Quiz")
        st.markdown("Escolha a quantidade de questões para começar:")
        
        total_questions = st.selectbox(
            "Número de questões:",
            options=[10, 20, 30, 40, 50],
            index=3,  # 40 questões como padrão
            help="Selecione quantas questões deseja responder"
        )
        
        st.markdown("")
        
        if st.button("🚀 Iniciar Quiz", type="primary", use_container_width=True):
            start_quiz(total_questions)
            st.rerun()


def show_question_screen():
    """Mostra a tela da questão atual"""
    if not st.session_state.questions:
        st.error("Nenhuma questão disponível!")
        return
    
    current_q = st.session_state.questions[st.session_state.current_question]
    total_questions = len(st.session_state.questions)
    progress = (st.session_state.current_question + 1) / total_questions
    
    # Cabeçalho
    st.title("🎓 Quiz TGE APP 2025")
    
    # Barra de progresso
    st.progress(progress, text=f"Questão {st.session_state.current_question + 1} de {total_questions}")
    
    # Mostrar resultado da questão anterior se houver
    if st.session_state.show_result and st.session_state.last_answer_correct is not None:
        if st.session_state.last_answer_correct:
            st.success("✅ **CORRETO!** Parabéns! Você acertou esta questão!")
        else:
            last_answer = st.session_state.user_answers[-1]
            st.error(f"❌ **INCORRETO!** Sua resposta: {last_answer['user_answer'].upper()} | Resposta correta: {last_answer['correct_answer'].upper()}")
        
        if st.button("➡️ Próxima Questão", type="primary"):
            next_question()
            st.rerun()
        return
    
    # Questão atual
    st.markdown("---")
    st.markdown(f"### Questão {st.session_state.current_question + 1}")
    st.markdown(f"**{current_q.enunciado}**")
    st.markdown(f"*Fonte: {current_q.fonte}*")
    
    # Alternativas
    st.markdown("#### Escolha sua resposta:")
    alternatives = current_q.get_alternatives()
    
    for letter, text in alternatives.items():
        if st.button(f"{letter.upper()}) {text}", key=f"btn_{letter}", use_container_width=True):
            answer_question(letter)
            st.rerun()


def show_final_results():
    """Mostra os resultados finais"""
    st.title("🎯 Resultado Final")
    
    total_questions = len(st.session_state.questions)
    correct_answers = st.session_state.correct_answers
    
    evaluator = PerformanceEvaluator()
    percentage, level, message = evaluator.evaluate_performance(correct_answers, total_questions)
    
    # Resumo geral
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Questões Corretas", f"{correct_answers}/{total_questions}")
    
    with col2:
        st.metric("Percentual", f"{percentage:.1f}%")
    
    with col3:
        if level == PerformanceLevel.EXCELLENT:
            st.metric("Desempenho", "Excelente", delta="🎉")
        elif level == PerformanceLevel.GOOD:
            st.metric("Desempenho", "Bom", delta="👍")
        else:
            st.metric("Desempenho", "Precisa Melhorar", delta="📚")
    
    # Mensagem de performance
    if level == PerformanceLevel.EXCELLENT:
        st.success(message)
    elif level == PerformanceLevel.GOOD:
        st.info(message)
    else:
        st.warning(message)
    
    # Revisão detalhada
    st.markdown("---")
    st.markdown("### 📋 Revisão Detalhada")
    
    with st.expander("Ver todas as respostas", expanded=False):
        for i, answer_data in enumerate(st.session_state.user_answers):
            question = answer_data['question']
            user_answer = answer_data['user_answer']
            correct_answer = answer_data['correct_answer']
            is_correct = answer_data['is_correct']
            
            if is_correct:
                st.success(f"**Questão {i+1}:** ✅ Correto")
            else:
                st.error(f"**Questão {i+1}:** ❌ Incorreto")
            
            st.markdown(f"**Pergunta:** {question.enunciado}")
            st.markdown(f"**Sua resposta:** {user_answer.upper()}) {question.get_alternatives()[user_answer]}")
            st.markdown(f"**Resposta correta:** {correct_answer.upper()}) {question.get_alternatives()[correct_answer]}")
            st.markdown(f"**Fonte:** {question.fonte}")
            st.markdown("---")
    
    # Botões de ação
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Tentar Novamente", type="primary", use_container_width=True):
            reset_quiz()
            st.rerun()
    
    with col2:
        if st.button("🏠 Novo Quiz", type="secondary", use_container_width=True):
            reset_quiz()
            st.rerun()


def main():
    """Função principal"""
    # Configurar página
    st.set_page_config(
        page_title="Quiz TGE APP 2025",
        page_icon="🎓",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    # CSS personalizado
    st.markdown("""
    <style>
        .stButton > button {
            margin: 5px 0;
            border-radius: 10px;
            border: none;
            padding: 10px 20px;
            font-weight: bold;
        }
        .stProgress > div > div {
            border-radius: 10px;
        }
        .stSelectbox > div > div {
            border-radius: 10px;
        }
        .stAlert {
            border-radius: 10px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Inicializar estado da sessão
    initialize_session_state()
    
    # Lógica principal da aplicação
    if not st.session_state.quiz_started:
        show_initial_screen()
    elif st.session_state.quiz_finished:
        show_final_results()
    else:
        show_question_screen()


if __name__ == "__main__":
    main()