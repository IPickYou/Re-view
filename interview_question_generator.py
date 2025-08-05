from dotenv import load_dotenv
from konlpy.tag import Okt
from langchain.chains import LLMChain
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

import os
import pandas as pd
import random
import re

class QuestionGenerator:
    def __init__(self):
        load_dotenv()

        # 질문 데이터셋 로드
        # 이 부분은 사용자가 이미 가지고 있는 CSV 파일을 사용합니다.
        # 예시로 'summary_experience_dataset.csv'와 'summary_new_dataset.csv'를 합쳐서 사용합니다.
        df_exp=pd.read_csv("summary_experience_dataset.csv")
        df_new=pd.read_csv("summary_new_dataset.csv")
        df_combined = pd.concat([df_exp['question_text'], df_new['question_text']], ignore_index=True)

        self.df_questions = pd.DataFrame({'question_text': df_combined})
        self.df_questions.to_csv('questions.csv')

        self.okt = Okt()

    # 텍스트 전처리 함수 (한국어 특화)
    def clean_text(self, text):
        text = re.sub(r"[^가-힣\s]", "", text) # 한글과 공백만 남기고 제거
        return text.strip()
    
    # 텍스트를 형태소 분석하여 명사만 추출하는 함수
    def tokenize_korean_text(self, text):
        return ' '.join(self.okt.nouns(self.clean_text(text)))
    
    def group_and_extract_questions(self, csv_file_path, num_clusters=5):
        """
        CSV 파일에서 질문을 로드하여 유사한 질문끼리 그룹화하고,
        각 그룹에서 랜덤으로 1개씩 질문을 추출합니다.

        Args:
            csv_file_path (str): 질문이 포함된 CSV 파일의 경로.
            num_clusters (int): 질문을 그룹화할 클러스터(그룹)의 개수.

        Returns:
            dict: 각 그룹에서 추출된 질문을 담은 딕셔너리.
                예: {'cluster_0': '질문 내용', 'cluster_1': '다른 질문 내용', ...}
        """
        try:
            df = self.df_questions
        except FileNotFoundError:
            print(f"오류: '{csv_file_path}' 파일을 찾을 수 없습니다.")
            return {}
        except Exception as e:
            print(f"CSV 파일 읽기 중 오류 발생: {e}")
            return {}

        if 'question_text' not in df.columns:
            print("오류: CSV 파일에 'question_text' 컬럼이 없습니다.")
            return {}

        # 텍스트 전처리 및 토큰화
        df['processed_question'] = df['question_text'].apply(self.tokenize_korean_text)

        # TF-IDF 벡터화
        # min_df를 조절하여 너무 자주 나오거나 너무 드물게 나오는 단어 필터링 가능
        vectorizer = TfidfVectorizer(max_features=1000, min_df=5, max_df=0.8)
        X = vectorizer.fit_transform(df['processed_question'])

        # K-Means 군집화
        # n_init='auto' 또는 명시적으로 횟수 지정 (예: 10)
        # n_init: KMeans 초기화 시도 횟수. 'auto'는 scikit-learn 버전 1.4부터 기본값이며, 이전 버전에서는 10이 일반적입니다.
        kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
        df['cluster'] = kmeans.fit_predict(X)

        extracted_questions = {}
        for cluster_id in range(num_clusters):
            cluster_questions = df[df['cluster'] == cluster_id]['question_text'].tolist()
            if cluster_questions:
                extracted_questions[f'Cluster_{cluster_id}'] = random.choice(cluster_questions)
            else:
                extracted_questions[f'Cluster_{cluster_id}'] = "해당 클러스터에 질문이 없습니다."
                
        return extracted_questions
    
    def get_clustered_dataframe(self, df_source, num_clusters=7):
        """
        원본 DataFrame을 받아 질문을 군집화하고, 'cluster' 컬럼이 추가된 DataFrame을 반환합니다.
        이 함수는 사용자가 제공한 'group_and_extract_questions' 함수의 핵심 군집화 로직을
        DataFrame을 직접 처리하도록 수정한 것입니다.
        
        Args:
            df_source (pd.DataFrame): 'question_text' 컬럼이 포함된 원본 DataFrame.
            num_clusters (int): 질문을 그룹화할 클러스터(그룹)의 개수.

        Returns:
            pd.DataFrame: 'processed_question' 및 'cluster' 컬럼이 추가된 DataFrame.
        """
        if df_source.empty or 'question_text' not in df_source.columns:
            print("오류: 입력 DataFrame이 비어있거나 'question_text' 컬럼이 없습니다.")
            return pd.DataFrame()

        df_copy = df_source.copy() # 원본 DataFrame을 변경하지 않도록 복사본 사용

        # 텍스트 전처리 및 토큰화
        df_copy['processed_question'] = df_copy['question_text'].apply(self.tokenize_korean_text)

        # TF-IDF 벡터화
        vectorizer = TfidfVectorizer(max_features=2000, min_df=5, max_df=0.8)
        X = vectorizer.fit_transform(df_copy['processed_question'])

        # K-Means 군집화
        kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
        df_copy['cluster'] = kmeans.fit_predict(X)

        return df_copy
    
    def generate_new_questions_for_cluster(self, cluster_id, clustered_df, llm_model, num_examples=5, num_to_generate=3):
        """
        특정 클러스터의 특징을 기반으로 새로운 질문을 생성합니다.

        Args:
            cluster_id (int): 질문을 생성할 클러스터의 ID.
            clustered_df (pd.DataFrame): 'cluster' 컬럼이 포함된 군집화된 DataFrame.
            llm_model: LangChain ChatOpenAI 객체.
            num_examples (int): 프롬프트에 포함할 클러스터 내 예시 질문의 개수.
            num_to_generate (int): 생성할 새로운 질문의 개수.

        Returns:
            list: 생성된 새로운 질문 리스트.
        """
        cluster_questions = clustered_df[clustered_df['cluster'] == cluster_id]['question_text'].tolist()

        if not cluster_questions:
            print(f"클러스터 {cluster_id}에 질문이 없습니다. 질문 생성을 건너뜝니다.")
            return []

        # 클러스터 내에서 무작위로 예시 질문 선택
        # 클러스터 내 질문 수가 num_examples보다 적으면 모든 질문 사용
        selected_examples = random.sample(cluster_questions, min(len(cluster_questions), num_examples))
        examples_str = "\n- ".join(selected_examples)

        # LLM 프롬프트 정의
        template = """
        당신은 면접 질문 생성 전문가입니다.
        아래는 특정 유형의 면접 질문 예시입니다. 이 예시들의 주제, 스타일, 질문의 의도 등을 고려하여,
        이와 유사한 새로운 면접 질문을 {num_to_generate}개 생성해 주세요.
        각 질문은 한 줄로 작성해 주시고, 번호를 붙여주세요.

        ---
        [면접 질문 예시]
        - {examples}
        ---

        [새로운 질문 생성]
        """
        prompt = PromptTemplate(input_variables=["examples", "num_to_generate"], template=template)
        chain = LLMChain(llm=llm_model, prompt=prompt)

        try:
            response = chain.invoke({
                "examples": examples_str,
                "num_to_generate": num_to_generate
            })

            if isinstance(response, dict) and "text" in response:
                generated_text = response["text"].strip()
            elif hasattr(response, "content"): # for newer langchain versions
                generated_text = response.content.strip()
            else:
                generated_text = str(response).strip() # Fallback

            # 생성된 텍스트를 줄바꿈 기준으로 리스트로 분리
            new_questions = [q.strip() for q in generated_text.split('\n') if q.strip()]
            return new_questions

        except Exception as e:
            print(f"LLM 질문 생성 중 오류 발생: {e}")
            return []
        
    def cluster_df(self):
        csv_file_path = 'questions.csv'
        try:
            df_questions = pd.read_csv(csv_file_path)
            if 'question_text' not in df_questions.columns:
                print("오류: CSV 파일에 'question_text' 컬럼이 없습니다.")
                exit()
            print(f"'{csv_file_path}'에서 {len(df_questions)}개 질문을 로드했습니다.")
        except Exception as e:
            print(f"CSV 파일 로드 실패: {e}")
            exit()

        # 군집화 실행
        num_clusters_to_use = 7
        print(f"\n{num_clusters_to_use}개 클러스터로 질문 군집화 중...")
        clustered_data_df = self.get_clustered_dataframe(df_questions, num_clusters=num_clusters_to_use)
        clustered_data_df.to_csv("question_clustered.csv")

    def generate(self):
        # --- 1. CSV 파일에서 DataFrame 로드 (이 부분은 사용자가 이미 가지고 있다고 가정) ---
        csv_file_path = 'question_clustered.csv' # 실제 CSV 파일 경로로 변경하세요.
        clustered_data_df = pd.read_csv(csv_file_path)

        if not clustered_data_df.empty:
            # --- 3. LangChain LLM 초기화 및 각 클러스터에서 새로운 질문 생성 ---
            if os.getenv("OPENAI_API_KEY") is None:
                print("\n오류: OPENAI_API_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인하거나 직접 설정해주세요. 질문 생성은 건너뜜니다.")
            else:
                llm = ChatOpenAI(model="gpt-4o", temperature=0.7, max_tokens=500) # 질문 생성에 적합한 모델과 설정

                all_generated_questions = {}
                num_clusters_to_use = 1
                for cluster_id in range(num_clusters_to_use):
                    generated_q_list = self.generate_new_questions_for_cluster(
                        cluster_id=cluster_id,
                        clustered_df=clustered_data_df, # 군집화된 DataFrame 전달
                        llm_model=llm,
                        num_examples=1, # 각 클러스터에서 5개의 예시를 LLM에 전달
                        num_to_generate=1 # 각 클러스터당 3개의 새로운 질문 생성 시도
                    )
                    if generated_q_list:
                        all_generated_questions[f'Cluster_{cluster_id}'] = generated_q_list

                if all_generated_questions:
                    res = []
                    for cluster_name, questions in all_generated_questions.items():
                        for q in questions:
                            res.append(q)

                    res = [re.sub(r'^\d+\.\s*', '', q) for q in res]

                    return res
                else:
                    print("생성된 질문이 없습니다.")
                    return []
        else:
            print("군집화할 데이터가 없거나 오류가 발생하여 추가 작업을 수행할 수 없습니다.")