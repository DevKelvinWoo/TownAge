# TownAge Map Layout — 맵 배치 도구

언리얼 에디터에서 도로, 밭, 건물의 영역을 지정하고 그 데이터로 테스트 형상을
만드는 도구입니다. 현재 형상은 엔진 기본 큐브를 늘린 도로/밭 판과 건물 박스입니다.
실제 건물 모델, 도로 텍스처, 작물 모델은 포함하지 않습니다.

## 사용 순서

1. 원하는 맵을 열고 **Tools → TownAge → TownAge Map Layout**을 엽니다.
   메뉴가 길면 아래로 스크롤하거나 메뉴 검색에서 TownAge를 찾습니다.
2. 패널을 뷰포트 옆에 놓거나 탭을 드래그해 도킹합니다. **New Layout**은 현재
   레벨에 배치 데이터 액터 하나만 추가합니다. 기존 액터가 있으면 Outliner에서
   선택하고 **Use Selected**를 누릅니다.
3. **Road / Field / Building**, **Type**을 고릅니다. 단위는 언리얼 cm입니다.
   도로 폭과 건물 높이를 조절한 다음 **Start Drawing**을 누릅니다.
4. 뷰포트의 바닥을 클릭합니다. XY는 배치 액터 기준 1m 격자에 맞춥니다.
   - **도로:** 경로 점을 두 개 이상 찍고 **Enter**로 완료합니다.
   - **밭 / 건물:** 사각형의 반대편 두 모서리를 찍으면 바로 생성합니다.
   - **Backspace:** 도로의 마지막 점을 뺍니다. **Esc:** 미완성 점만 취소합니다.
   - Alt를 누른 카메라 조작은 기존 에디터 동작을 유지합니다.
5. **Select / Move**에서 형상을 클릭하거나 목록 행을 고릅니다. 이동 기즈모로
   위치를 바꿉니다. **Focus**는 해당 영역을 화면에 맞추며, **Delete Element**는
   해당 배치 데이터만 삭제합니다. **Ctrl+Z / Ctrl+Y**로 실행 취소/다시 실행합니다.
6. 선택한 배치의 이름, 같은 분류의 Type ID, 폭/높이를 수정한 뒤
   **Apply Selected Changes**를 누릅니다. 정확한 모서리 좌표는 **Layout Details**의
   `Elements → Points`에서도 수정할 수 있습니다.
7. **맵을 저장**하면 배치 데이터가 보존됩니다. 형상은 데이터에서 다시 만들어집니다.
   **Export JSON / Import JSON**은 버전이 있는 배치 데이터를 주고받습니다.
   가져오기는 현재 배치 액터의 데이터를 교체하며, 잘못된 입력은 기존 내용을
   유지합니다. 정상 가져오기도 실행 취소할 수 있습니다.

## 종류 추가와 나중의 모델 교체

**Layout Details → Map Layout → Types**가 배치별 카탈로그입니다.

| 분류 | 기본 Type ID | 현재 용도 |
| --- | --- | --- |
| Road | `road.path`, `road.stone` | 서로 다른 도로 종류 |
| Field | `field.soil`, `field.orchard` | 서로 다른 밭/과수원 영역 |
| Building | `building.house`, `building.shop` | 서로 다른 건물 종류 |

종류를 더 만들려면 Types에 항목을 추가하고 고유한 `TypeId`, `Kind`, `DisplayName`을
지정합니다. 실제 아트가 준비되면 그 항목의 **Mesh / Material**에 에셋을 연결합니다.
같은 ID를 참조하는 배치가 모두 해당 모델로 재생성됩니다. 기존 배치가 참조하는
ID는 유지하고 표시 이름이나 에셋만 바꾸십시오. 잘못된 ID/분류는 검증 오류가 됩니다.

모델은 로컬 **X=길이, Y=폭, Z=높이** 기준 실제 메시 bounds/pivot을 사용해 영역에
맞춥니다. 건물은 지정한 높이로, 도로/밭은 얇은 판으로 맞추므로 종횡비가 다른
메시는 늘어날 수 있습니다. Mesh만 교체하면 메시의 기존 머티리얼을 유지하고,
Material까지 지정하면 모든 머티리얼 슬롯에 그 오버라이드를 적용합니다.

카탈로그/배치 좌표는 액터마다 독립적입니다. 배치 액터 자체를 이동/회전하면 전체
구역이 함께 움직입니다. 개별 사각형 회전이나 곡선/다각형 밭은 현재 범위에 없으며,
필요하면 구역별 배치 액터를 사용하십시오.

## 데이터와 안전 범위

- `ATownAgeMapLayout`은 안정적인 GUID, 종류 ID, 이름, 로컬 좌표, 폭/높이를 저장합니다.
  JSON schemaVersion=1에는 액터 transform, Types, Elements가 포함됩니다.
- 생성된 ISM 컴포넌트는 임시 파생 형상입니다. 같은 종류는 인스턴싱하며, 다시
  만들 때 **이 액터가 생성한 컴포넌트만** 정리합니다. 맵의 다른 액터는 지우지 않습니다.
- 에디터 재열기 시 형상을 복원하고, 게임에서는 `PostInitializeComponents`에 생성해
  플레이어 시작 위치의 충돌 판정보다 먼저 준비합니다. 서버/클라이언트는 같은 맵의
  동일한 데이터로 정적 형상을 구성합니다. 실행 중 클라이언트 편집 RPC는 없습니다.
- 에디터 플러그인은 게임 패키지에서 제외됩니다. 플레이 중에는 저작 UI를 비활성화합니다.
- 한 배치에 최대 256종류, 5,000영역, 50,000인스턴스, 도로당 512점으로 제한합니다.
  이것은 입력 상한이지 모바일 권장 예산이나 성능 보증이 아닙니다.
- 기존 Landscape를 깎거나 칠하지 않습니다. 도로는 지정점 사이의 직선 판이며,
  밭과 건물은 **평평한 사각 영역**입니다. 경사지에 자동으로 밀착/테라포밍하지
  않으므로 평지에서 사용하거나 Z와 경로 점을 조절하십시오. 겹침은 저작자가 결정합니다.
- 게임 중 배치 편집, 멀티유저 에디터 동시 편집, 실행 중 레이아웃 스트리밍/변경,
  네트워크 편집 권한 관리, 건물 문/농사 게임플레이 자동 연결은 포함하지 않습니다.

## 검토 맵과 재현

로컬 검토 맵은 `/Game/Maps/Tools/L_MapLayout_Review01`입니다. 도로 2개, 밭 2개,
건물 3개를 6종류로 배치한 예시이며 시작/기본 맵은 변경하지 않습니다. `.umap`은
로컬에만 두고 소스/예시 JSON만 게시합니다.

```powershell
& 'E:/UE/UE_5.8/Engine/Build/BatchFiles/Build.bat' TownAgeEditor Win64 Development "$PWD/TownAge.uproject" -WaitMutex -NoHotReloadFromIDE
& 'E:/UE/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$PWD/TownAge.uproject" -run=pythonscript "-script=$PWD/Tools/MapLayout/create_review_map.py" -unattended -nullrhi -nosound
```

생성 스크립트는 기존 맵을 덮어쓰지 않습니다. `-MapLayoutResumeReview`는 이 도구가
만들다 중단한 미완성 검토 맵에만 사용하며, 완료 보고서나 다른 액터가 있으면 거부합니다.

- `open_review.py`: 새 에디터에서 저장된 맵의 7영역/9인스턴스 자동 복원을 검증합니다.
- `verify_play.py`: 해당 맵에서 PIE 형상 수, 중복 여부, 충돌 프로필을 확인합니다.
- `capture_state.py`: 마우스 조작 뒤 실제 배치 좌표를 읽기 전용으로 기록합니다.
- `verify_move.py`: 기즈모와 동일한 이동 델타 핸들러를 재생해, 선택한 배치만 이동하고
  실행 취소/다시 실행이 좌표와 형상을 복원하는지 확인합니다.
- 에디터 전용 `TownAgeMapEditorLibrary`는 Python/에디터 스크립트의 JSON 입출력을
  지원합니다. 게임 모듈에 저작 UI나 에디터 의존성을 추가하지 않습니다.
- `Automation RunTests TownAge`에 데이터 검증, JSON 왕복/실패 보존, 메시 교체,
  반복 재생성, 플레이 전 충돌 회귀 검증이 포함됩니다.

로그/보고서는 `Saved/MapLayout`, `Saved/Logs/MapLayout*.log`에 남깁니다.
실제 Android/iOS 패키징 및 기기 성능은 데스크톱 에디터 검증과 별개입니다.

로컬 검증: Editor/게임 Win64 Development 빌드, TownAge 자동화 테스트 11개,
저장 맵 재열기(7영역/9인스턴스), 네이티브 마우스의 도로/밭/건물 배치·선택·삭제,
실행 취소/다시 실행, 실제 파일 대화상자의 JSON 입출력, PIE의 중복 없는 9인스턴스와
충돌 프로필을 확인했습니다. 자동 입력 드라이버의 드래그는 UE 원시 마우스 델타를
발생시키지 않아, 축 선택은 네이티브 입력으로 확인하고 좌표 이동은 동일한 네이티브
콜백 재생으로 별도 검증했습니다. 실제 하드웨어 마우스의 종단 간 드래그, Android/iOS
기기 및 패키지, 완성 맵의 다중 클라이언트 접속/성능 검증은 별도입니다.

개발 진단이 필요하면 에디터에 `-MapLayoutDebugInput`을 붙이면 입력 축/델타 로그가
남습니다. 에디터 배치 스크립트는 `TownAgeMapEditorLibrary.translate_element`로 같은
이동 핸들러를 사용할 수 있습니다. 샘플 원본 데이터는 `Examples/ReviewLayout.json`입니다.
