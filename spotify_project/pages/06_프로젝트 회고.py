# pages/06_project_reflection.py
import streamlit as st

st.set_page_config(page_title="프로젝트 후기", layout="wide")

st.markdown("""
<h2 style="margin-bottom:16px;">프로젝트 회고: Spotify 메타데이터 수집·대시보드 구축</h2>
<p class="lead">API 인증–데이터 정합성–협업 프로세스까지, 처음부터 끝까지 실행하며 얻은 인사이트를 정리했습니다.</p>

<div class="stage-card">
  <h4>1. 인증/호출 안정화</h4>
  <ul>
    <li>Access Token 만료로 연속 호출 실패 → OAuth 2.0 흐름과 <code>requests</code> 재시도 패턴을 적용.</li>
    <li>예외/로그 표준화로 오류 재현성 확보(요청·응답 스냅샷, 상태코드·헤더 기록).</li>
  </ul>
</div>

<div class="stage-card">
  <h4>2. 데이터 정합성 확보</h4>
  <ul>
    <li>중복 <code>track_id</code> 다수 → 키 기준 중복 제거 및 스키마 통일(popularity, release_date, explicit).</li>
    <li>JSON 필드 결측/형변환 이슈 사전 처리 → Pandas 파이프라인으로 일괄 전처리.</li>
  </ul>
</div>

<div class="stage-card">
  <h4>3. 수집 성능과 제한 대응</h4>
  <ul>
    <li>Rate Limit 대응: Batch 호출·간격 제어(<code>sleep</code>)·백오프 전략으로 누락 최소화.</li>
    <li>반복 호출 캐시·로컬 저장을 도입해 수집 속도 개선 및 API 비용 절감.</li>
  </ul>
</div>

<div class="stage-card">
  <h4>4. 협업 과정에서의 교훈</h4>
  <ul>
    <li><b>의사소통 단일 채널</b> – 오디오 특성 로드 이슈 공유 누락으로 재작업 발생 → 중요 이슈는 공용 채널에 <u>요약+재현 방법</u>까지 게시.</li>
    <li><b>수집 방식 일관화</b> – 일부는 웹 API, 일부는 CSV로 진행하며 일관성 붕괴 → 사전에 <u>접근법·도구·스키마</u>를 합의하고 문서화.</li>
    <li><b>모듈화</b> – 초기 복붙 코드로 유지보수 난항 → 공용 <code>utils.py</code>로 API/전처리 함수 표준화하여 재사용성 향상.</li>
    <li><b>버전 관리</b> – 파일을 직접 주고받다 최신본 추적 어려움·코드 혼합 발생 → <u>Git Flow</u>(feature → PR → review → main)와 커밋 컨벤션 적용의 필요성 확인.</li>
  </ul>
</div>

<div class="stage-card">
  <h4>5. 다음 단계(구체안)</h4>
  <ul>
    <li><b>신뢰성</b> – 토큰 자동 갱신, 지수 백오프로 재시도, 실패 큐·재처리 잡 도입.</li>
    <li><b>성능</b> – 요청 병렬화(쿼터 내), 응답 캐시(<code>etag</code>/hash), 증분 수집 파이프라인.</li>
    <li><b>데이터</b> – 스키마 버전 관리, 테스트 데이터셋/검증 규칙(중복·결측·범위) 자동화.</li>
    <li><b>협업</b> – PR 템플릿, 코드리뷰 체크리스트, 릴리스 노트·CHANGELOG 운영.</li>
  </ul>
</div>

<style>
:root{ --text:#0f172a; --muted:#64748b; --accent:#ff4500; }
.lead{ color:var(--muted); margin-bottom:20px; }
.stage-card {
  background: #ffffff;
  color: var(--text);
  padding: 18px 20px;
  border-radius: 14px;
  border: 1px solid #eef1f5;
  box-shadow: 0 2px 10px rgba(2,6,23,0.06);
  margin-bottom: 16px;
}
.stage-card h4 {
  margin: 0 0 10px 0;
  color: var(--accent);
  font-weight: 700;
}
.stage-card ul { padding-left: 18px; margin: 0; }
.stage-card li { margin-bottom: 6px; line-height: 1.5; }
h2,h4,p,li { color: var(--text); }
</style>
""", unsafe_allow_html=True)
