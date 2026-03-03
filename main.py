from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
import pandas as pd
import numpy as np
import collections

class Answer(BaseModel):
    attribute: str
    operator: str
    value: Any

class AkinatorRequest(BaseModel):
    answers: List[Answer] = []
    step: int = 1

app = FastAPI(title="H!P-Navigator Backend API")

# Load and preprocess data
df = pd.read_csv("hp_master_knowledge_v6.0.csv")
df['semantic_tags'] = df['semantic_tags'].fillna("")

def filter_songs(q: Optional[str], tag: Optional[str], fame: Optional[str], mood: Optional[str], bpm_min: Optional[int], bpm_max: Optional[int]) -> pd.DataFrame:
    result_df = df.copy()

    # Keyword search
    if q:
        q_lower = q.lower()
        mask = result_df['title'].str.lower().str.contains(q_lower, na=False) | \
               result_df['artist_name'].str.lower().str.contains(q_lower, na=False)
        result_df = result_df[mask]

    # Tag search
    if tag:
        tag_lower = tag.lower()
        result_df = result_df[result_df['semantic_tags'].str.lower().str.contains(tag_lower, na=False)]

    # Fame search
    if fame:
        if fame == "standard":
            result_df = result_df[result_df['fame_score'] >= 0.3]
        elif fame == "hidden":
            result_df = result_df[(result_df['fame_score'] >= 0.1) & (result_df['fame_score'] < 0.4)]
        elif fame == "manic":
            result_df = result_df[result_df['fame_score'] < 0.1]

    # Mood search (0.8以上のパーセンタイル)
    if mood:
        mood_col = f"score_{mood}"
        if mood_col in df.columns:
            threshold = df[mood_col].quantile(0.8)
            result_df = result_df[result_df[mood_col] >= threshold]

    # BPM search (tempo)
    if bpm_min is not None:
        result_df = result_df[result_df['tempo'] >= bpm_min]
    if bpm_max is not None:
        result_df = result_df[result_df['tempo'] <= bpm_max]

    return result_df

@app.get("/search")
def search(
    q: Optional[str] = Query(None, description="キーワード（曲名・アーティスト名）"),
    tag: Optional[str] = Query(None, description="セマンティックタグ"),
    fame: Optional[str] = Query(None, description="知名度 (standard, hidden, manic)"),
    mood: Optional[str] = Query(None, description="感情スコア (euphoria, sentimental, struggle等)"),
    bpm_min: Optional[int] = Query(None, description="最小BPM"),
    bpm_max: Optional[int] = Query(None, description="最大BPM"),
):
    result_df = filter_songs(q, tag, fame, mood, bpm_min, bpm_max)

    if len(result_df) == 0:
        return []

    n_samples = min(3, len(result_df))
    sampled_df = result_df.sample(n=n_samples)

    sampled_df = sampled_df.replace({np.nan: None})
    records = sampled_df.to_dict(orient="records")
    return records

@app.get("/concierge")
def concierge(
    q: Optional[str] = Query(None, description="キーワード（曲名・アーティスト名）"),
    tag: Optional[str] = Query(None, description="セマンティックタグ"),
    fame: Optional[str] = Query(None, description="知名度 (standard, hidden, manic)"),
    mood: Optional[str] = Query(None, description="感情スコア (euphoria, sentimental, struggle等)"),
    bpm_min: Optional[int] = Query(None, description="最小BPM"),
    bpm_max: Optional[int] = Query(None, description="最大BPM"),
    step: int = Query(1, description="現在の質問ステップ数")
):
    result_df = filter_songs(q, tag, fame, mood, bpm_min, bpm_max)
    remaining_count = len(result_df)

    if remaining_count <= 20 or step >= 5:
        if remaining_count == 0:
            return {"status": "finished", "remaining_count": 0, "songs": []}
            
        n_samples = min(3, remaining_count)
        sampled_df = result_df.sample(n=n_samples)
        sampled_df = sampled_df.replace({np.nan: None})
        records = sampled_df.to_dict(orient="records")
        return {"status": "finished", "remaining_count": remaining_count, "songs": records}

    # Step 3: 動的ヒント生成 (remaining_count > 20 and step < 5)
    hint = {}
    
    # テンポの差分チェック
    tempo_max = result_df['tempo'].max()
    tempo_min = result_df['tempo'].min()
    
    if pd.notna(tempo_max) and pd.notna(tempo_min) and (tempo_max - tempo_min) > 40:
        hint = {
            "attribute": "tempo",
            "options": ["アップテンポ", "バラード"]
        }
    else:
        # tagの頻出チェック
        all_tags = []
        for tags_str in result_df['semantic_tags']:
            if pd.notna(tags_str) and isinstance(tags_str, str) and tags_str.strip():
                tags = [t.strip() for t in tags_str.split(',') if t.strip()]
                all_tags.extend(tags)
        
        if all_tags:
            tag_counts = collections.Counter(all_tags)
            if tag:
                exclude_tag = tag.lower()
                top_tags = [t for t, _ in tag_counts.most_common() if t.lower() != exclude_tag][:3]
            else:
                top_tags = [t for t, _ in tag_counts.most_common(3)]
                
            if len(top_tags) > 0:
                hint = {
                    "attribute": "tag",
                    "options": top_tags
                }
            else:
                 hint = {
                    "attribute": "mood",
                    "options": ["euphoria", "sentimental", "struggle"]
                }
        else:
            hint = {
                "attribute": "mood",
                "options": ["euphoria", "sentimental", "struggle"]
            }

    return {
        "status": "questioning",
        "remaining_count": remaining_count,
        "next_hints": hint
    }

@app.post("/akinator")
def akinator(request: AkinatorRequest):
    result_df = df.copy()
    
    # Step 1: 履歴に基づくフィルタリング
    for ans in request.answers:
        attr = ans.attribute
        op = ans.operator
        val = ans.value
        
        if attr not in result_df.columns:
            continue
            
        if op == "==":
            result_df = result_df[result_df[attr] == val]
        elif op == ">=":
            try:
                val_float = float(val)
                result_df = result_df[result_df[attr] >= val_float]
            except ValueError:
                result_df = result_df[result_df[attr] >= val]
        elif op == "<=":
            try:
                val_float = float(val)
                result_df = result_df[result_df[attr] <= val_float]
            except ValueError:
                result_df = result_df[result_df[attr] <= val]
        elif op == "contains":
            result_df = result_df[result_df[attr].astype(str).str.contains(str(val), na=False, regex=False)]
            
    remaining_count = len(result_df)
    
    # Step 2: 終了判定
    if remaining_count <= 3 or request.step >= 15:
        if remaining_count == 0:
            return {"status": "finished", "remaining_count": 0, "songs": []}
            
        sampled_df = result_df.replace({np.nan: None})
        records = sampled_df.to_dict(orient="records")
        return {"status": "finished", "remaining_count": remaining_count, "songs": records}

    # Step 3: 次問の計算 (情報利得の最大化 ≈ 0.5に近い割合)
    best_diff = float('inf')
    best_question = None
    
    def evaluate_split(mask, question_dict):
        nonlocal best_diff, best_question
        if remaining_count == 0:
            return
        p = mask.sum() / remaining_count
        diff = abs(p - 0.5)
        if diff < best_diff:
            best_diff = diff
            best_question = question_dict

    # 候補1: アーティスト
    if not result_df['artist_name'].dropna().empty:
        top_artist = result_df['artist_name'].mode().iloc[0]
        evaluate_split(result_df['artist_name'] == top_artist, {
            "attribute": "artist_name",
            "operator": "==",
            "value": top_artist
        })

    # 候補2: タグ
    used_tags = [ans.value for ans in request.answers if ans.attribute in ('tag', 'semantic_tags')]
    all_tags = []
    for tags_str in result_df['semantic_tags']:
        if pd.notna(tags_str) and isinstance(tags_str, str):
            tags = [t.strip() for t in tags_str.split(',') if t.strip()]
            all_tags.extend(tags)
            
    if all_tags:
        tag_counts = collections.Counter(all_tags)
        for t, _ in tag_counts.most_common():
            if t not in used_tags:
                mask = result_df['semantic_tags'].str.contains(t, na=False, regex=False)
                evaluate_split(mask, {
                    "attribute": "semantic_tags",
                    "operator": "contains",
                    "value": t
                })
                break
                
    # 候補3: テンポ
    if not result_df['tempo'].dropna().empty:
        tempo_median = float(result_df['tempo'].median())
        evaluate_split(result_df['tempo'] >= tempo_median, {
            "attribute": "tempo",
            "operator": ">=",
            "value": tempo_median
        })
        
    # 候補4: 知名度
    if not result_df['fame_score'].dropna().empty:
        fame_median = float(result_df['fame_score'].median())
        evaluate_split(result_df['fame_score'] >= fame_median, {
            "attribute": "fame_score",
            "operator": ">=",
            "value": fame_median
        })
        
    if not best_question:
        best_question = {"attribute": "tempo", "operator": ">=", "value": 120}

    return {
        "status": "questioning",
        "remaining_count": remaining_count,
        "next_question": best_question
    }
