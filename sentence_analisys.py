from collections import Counter
from dotenv import load_dotenv
from konlpy.tag import Okt
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from transformers import T5ForConditionalGeneration, PreTrainedTokenizerFast

import re

class SentenceAnalyzer:
    def __init__(self):
        load_dotenv() # 환경 변수 로드
        self.okt = Okt() # 형태소 분석기 초기화
        self.stopwords = set(["그", "저", "것", "이", "저는", "제가", "근데", "좀", "그냥", "정말", "되게", "음", "뭐"]) # 불용어 설정
        self.fillers = {"어", "음", "아", "그", "저기", "뭐", "응", "흠"} # 필러 단어 설정

        # LLM 프롬프트 템플릿 설정
        self.prompt_template = PromptTemplate.from_template("""
        너는 인공지능 면접관이다.  
        다음은 면접 질문과 지원자의 답변이다.  
        아래의 절차에 따라 평가를 수행하라.

        ---

        🔹 단계 1: 질문을 핵심 요소로 분해하라.  
        예: 질문 = "A와 B에 대해 설명해달라" → 요소1: A에 대한 설명, 요소2: B에 대한 설명

        🔹 단계 2: 각 요소가 답변에서 명시적으로 언급되었는지 여부를 판단하라.  
        답변에 요소가 간접적으로 암시되었더라도 명시적으로 언급되지 않으면 "없음"으로 판단한다.

        🔹 단계 3: 아래 평가 기준에 따라 “있다 / 없다”로 결과를 출력한다.  
        특히 1번 항목(질문 이해 및 연관성)은, 질문의 모든 구성 요소가 빠짐없이 포함된 경우에만 "있다"로 평가한다.  
        하나라도 누락되었으면 반드시 "없다"로 평가한다.

        ---

        ### 면접 질문:
        {question}

        ### 지원자 답변:
        {answer}


        ### 질문 구성 요소:
        - 요소1: ...
        - 요소2: ...
        (예시: Transformer의 장점 설명, 프로젝트 활용 경험 설명)


        ### 답변 대응 여부:
        - 요소1: 있음 / 없음
        - 요소2: 있음 / 없음
        ※ 절대 기준: 질문의 구성 요소 중 하나라도 빠지면 "질문 이해 및 연관성"은 "없다"로 평가할 것.
        ---
        출력 예시
        ---                                       
        ### 평가 결과:
        [인성 평가]  
        1. 질문 이해 및 연관성: [ ]  
        2. 자기 성찰 및 경험 활용: [ ]  
        3. 태도 및 소통 역량: [ ]

        [기술 평가]  
        4. 지식의 정확성과 깊이: [ ]  
        5. 적용 및 실무 경험: [ ]  
        6. 문제 해결 및 응용력: [ ]
        """)

    # 텍스트 정제 함수
    def clean_text(self, text):
        text = re.sub(r"[^가-힣\s]", "", text)
        return text.strip()

    # 키워드 추출 함수
    def extract_keywords(self, texts, min_len=2, top_k=20):
        counter = Counter()
        for text in texts:
            text = self.clean_text(text)
            nouns = self.okt.nouns(text)
            nouns = [n for n in nouns if len(n) >= min_len and n not in self.stopwords]
            counter.update(nouns)
        return counter.most_common(top_k)
    
    # 문장 끝 단어 추출 함수
    def extract_sentence_endings(self, texts):
        endings = []
        for text in texts:
            sentences = re.split(r'[.!?]', text)
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence:
                    morphs = self.okt.morphs(sentence)
                    if morphs:
                        endings.append(morphs[-1])
        return Counter(endings).most_common(10)
    
    # 필러 단어 추출 함수
    def extract_fillers(self, texts):
        filler_counter = Counter()
        for text in texts:
            morphs = self.okt.morphs(text)
            filler_counter.update([m for m in morphs if m in self.fillers])
        return filler_counter.most_common(10)
    
    # 사용자 스타일 분석 함수
    def analyze_user_style(self, texts):
        result = {}
        result["keywords"] = self.extract_keywords(texts) # 키워드 추출
        result["endings"] = self.extract_sentence_endings(texts) # 문장 끝 단어 추출
        result["fillers"] = self.extract_fillers(texts) # 필러 단어 추출
        return result
    
    # 답변 평가 함수
    def evaluate_answer(self, question, answer, model_name="gpt-4o"):
        # LLM chain 설정
        llm = ChatOpenAI(model=model_name, temperature=0)
        chain = LLMChain(llm=llm, prompt=self.prompt_template)

        # 답변 평가 실행
        result = chain.run({
            "question": question,
            "answer": answer
        })
        
        return result
    
    def summarize(self, target):
        # 모델 로드
        model_id = "aimer3152/summary_model"
        tokenizer = PreTrainedTokenizerFast.from_pretrained(model_id)
        model = T5ForConditionalGeneration.from_pretrained(model_id)

        input_text = "summarize: " + target.strip() # T5 스타일의 입력 프롬프트 구성
        inputs = tokenizer.encode(input_text, return_tensors="pt", max_length=512, truncation=True) # 토크나이징
        summary_ids = model.generate(inputs, max_length=100, min_length=10, length_penalty=2.0, num_beams=4, early_stopping=True) # 요약 생성
        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True) # 결과 디코딩

        return summary