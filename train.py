import pandas as pd
from datasets import Dataset, DatasetDict
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, TrainingArguments, Trainer, DataCollatorForSeq2Seq
import torch
import numpy as np
import evaluate
import nltk
from accelerate import Accelerator # <--- Accelerator 임포트

# NLTK punkt 토크나이저 다운로드 (최초 1회 실행)
try:
    nltk.data.find('tokenizers/punkt')
except nltk.downloader.DownloadError:
    nltk.download('punkt')
    print("NLTK 'punkt' tokenizer downloaded.")

# --- 데이터 로드 및 전처리 (이전과 동일) ---
file_path = "C:/나이스/summary_experience_dataset.csv"
try:
    df = pd.read_csv(file_path)
    qa_df = df[['answer_text', 'summary_text']].copy()
    full_dataset = Dataset.from_pandas(qa_df)
    train_test_split_dataset = full_dataset.train_test_split(test_size=0.1, seed=42)
    raw_datasets = DatasetDict({
        'train': train_test_split_dataset['train'],
        'validation': train_test_split_dataset['test']
    })
except Exception as e:
    print(f"데이터 로드 및 분할 중 오류 발생: {e}")
    exit()

model_checkpoint = "eenzeenee/t5-base-korean-summarization"
tokenizer = AutoTokenizer.from_pretrained(model_checkpoint)

max_input_length = 512
max_target_length = 128

def preprocess_function(examples):
    inputs = ["summarize: " + doc for doc in examples["answer_text"]]
    model_inputs = tokenizer(inputs, max_length=max_input_length, truncation=True)
    labels = tokenizer(text_target=examples["summary_text"], max_length=max_target_length, truncation=True)
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

print("\n토큰화 시작...")
tokenized_datasets = raw_datasets.map(preprocess_function, batched=True)
print("토큰화 완료.")

# 모델 로드 및 Gradient Checkpointing 활성화
print("\n모델 로드 중...")
model = AutoModelForSeq2SeqLM.from_pretrained(model_checkpoint)
model.gradient_checkpointing_enable()
print("모델 로드 완료.")

# 데이터 콜레이터 설정
data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

# 평가 지표 로드 (ROUGE)
metric = evaluate.load("rouge")

def postprocess_text(preds, labels):
    preds = [pred.strip() for pred in preds]
    labels = [label.strip() for label in labels]
    preds = ["\n".join(nltk.sent_tokenize(pred)) for pred in preds]
    labels = ["\n".join(nltk.sent_tokenize(label)) for label in labels]
    return preds, labels

def compute_metrics(eval_preds):
    preds, labels = eval_preds
    if isinstance(preds, tuple):
        preds = preds[0]
    decoded_preds = tokenizer.batch_decode(preds, skip_special_tokens=True)
    labels = np.where(labels != -100, labels, tokenizer.pad_token_id)
    decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)
    decoded_preds, decoded_labels = postprocess_text(decoded_preds, decoded_labels)
    result = metric.compute(predictions=decoded_preds, references=decoded_labels, use_stemmer=True)
    result = {k: v * 100 for k, v in result.items()}
    prediction_lens = [np.count_nonzero(pred != tokenizer.pad_token_id) for pred in preds]
    result["gen_len"] = np.mean(prediction_lens)
    return {k: round(v, 4) for k, v in result.items()}

# 트레이닝 인자 설정
training_args = TrainingArguments(
    output_dir="./t5_korean_summarization_results",
    eval_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4, # 배치 1 * 4 = 실질 배치 4
    per_device_eval_batch_size=1,
    weight_decay=0.01,
    save_total_limit=3,
    num_train_epochs=3,
    fp16=torch.cuda.is_available(),
    gradient_checkpointing=True,
    push_to_hub=False,
    logging_dir="./logs",
    logging_steps=500,
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="rouge1",
    report_to="tensorboard",
)

# Trainer 인스턴스 생성
print("\nTrainer 인스턴스 생성 중...")
# Trainer가 accelerate 설정을 자동으로 감지하고 사용합니다.
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["validation"],
    tokenizer=tokenizer,
    data_collator=data_collator,
    compute_metrics=compute_metrics,
)
print("Trainer 인스턴스 생성 완료.")

# 학습 시작
print("\n모델 학습 시작...")
# 학습을 accelerate 명령어로 시작해야 합니다.
# 이 파이썬 스크립트를 직접 실행하는 대신, 터미널에서 아래와 같이 실행합니다.
# accelerate launch your_script_name.py
trainer.train() # 이 부분은 accelerate launch가 처리합니다.
print("모델 학습 완료.")

# 학습된 모델 사용 부분은 이전과 동일하게 유지됩니다.
# ... (생성 코드 생략)