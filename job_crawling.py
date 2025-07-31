from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils import OpenAIClient

import re
import time

class JobCrawler:
    def __init__(self):
        load_dotenv()
        self.openai_client = OpenAIClient()

    # 원티드 채용 공고 웹 크롤링
    def extract_wanted_job_text_selenium(self, url):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")

        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(5)

        wait = WebDriverWait(driver, 20)
        try:
            button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[span[contains(text(), '상세 정보 더 보기')]]"))
            )
            wait.until(EC.visibility_of(button))

            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
            time.sleep(1)

            driver.execute_script("""
                const blocker = document.querySelector('div.WantedApplyBtn_container__lBx_L');
                if (blocker) { blocker.remove(); }
            """)

            time.sleep(0.5)

            driver.execute_script("arguments[0].click();", button)

            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.JobDescription_JobDescription__paragraph__87w8I"))
            )
            time.sleep(1)
        except Exception as e:
            print("상세 정보 더 보기 버튼 클릭 실패 또는 없음:", e)
            driver.save_screenshot("error_screenshot.png")

        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()

        containers = soup.find_all('div', class_='JobDescription_JobDescription__paragraph__87w8I')
        if not containers:
            print("채용 공고 본문을 찾지 못했습니다.")
            return None

        texts = [c.get_text(separator='\n', strip=True) for c in containers]
        text = '\n\n'.join(texts)
        return text
    
    def generate_interview_questions(self, job_text):
        prompt = f"""
        다음은 채용 공고 내용입니다. 이 내용을 바탕으로 면접관이 물어볼 수 있는 질문을 5~10개 예상해 주세요.
        구체적으로, 업무 수행 능력, 역량, 성향, 지원 동기, 경험 중심의 질문 위주로 작성해 주세요.
        그리고 응답할 때는 예상 질문 문장만 응답하세요.

        [채용 공고]
        {job_text}

        [예상 면접 질문]
        """
        response = self.openai_client.create_response(
            user_content = prompt,
            temperature = 0.7
        )
        return response
    
    def extract_text(self, text):
        # 숫자+점+공백으로 시작하는 부분을 기준으로 split
        res = re.split(r'\d+\.\s*', text.strip())
        # 첫 번째 요소는 빈 문자열일 수 있으니 제거
        res = [q.strip() for q in res if q.strip()]
        return res
    
    def generate_interview_answers(self, questions):
        prompt = f"""
        다음은 면접 예상 질문입니다. 이 내용을 바탕으로 면접관이 만족할 수 있는 모범답안들을 예상해 주세요.
        구체적으로, 질문에 담긴 업무 수행 능력, 역량, 성향, 지원 동기, 경험을 키워드로 문맥에 맞게 작성해 주세요.
        그리고 응답할 때는 예상 답변 문장만 응답하세요.

        [예상 면접 질문]
        {chr(10).join(f"{i+1}. {q}" for i, q in enumerate(questions))}

        [모범 답안]
        """
        response = self.openai_client.create_response(
            user_content = prompt,
            temperature = 0.7
        )
        return response