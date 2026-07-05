# 1주차 전체 회고 (학습 내용 정리 및 종합 회고)

## 개별 파일 접근
1. [7월 1일 회고](0701.md)
2. [7월 2일 회고](0702.md)
3. [7월 3일 회고](0703.md)

## 학습 내용 정리

1. [7월 1일](#7월-1일)
2. [7월 2일](#7월-2일)
3. [7월 3일](#7월-3일)

### 7월 1일
소프티어 첫 날로 간단한 OT와 함께 데이터 엔지니어에 대해 소개를 들었다.
특별히 뭔가 학습을 하지는 않았고, 음 개요 느낌으로 진행했다. 이래서 DE가 중요하고, DA가 중요하고 이러한 것들에 대해 설명을 들었다.

그리고 이 날 1주차 미션1을 시작했다.

미션 1의 경우에는 mtcars 데이터셋을 기반으로 pandas와 matplotlib를 다루는 연습을 하는 것이었다.

미션 1을 진행하며, 아래와 같은 내용을 학습했다.

1. [pandas](https://pandas.pydata.org/docs/)를 이용한 DataFrame 정보 조회
    - 함수
        - head : 상위 N개 레코드 조회 (기본은 5개)
            ```python
            df.head() # 상위 5개 조회
            df.head(10) # 상위 10개 조회
            ```
        - tail : 하위 N개 레코드 조회 (기본은 5개)
            ```python
            df.tail() # 하위 5개 조회
            df.tail(10) # 하위 10개 조회
            ```
        - info : DataFrame의 요약 정보 출력
            ```python
            # DataFrame.info(verbose=None, buf=None, max_cols=None, memory_usage=None, show_counts=None)
            # verbose -> 전체 요약 정보를 출력할지 말지 (False로 하면 요약 정보로 출력)
            # buf -> output을 어디로 보낼지, 기본은 stdout (버퍼로 설정가능)
            # memory_usage -> DataFrame의 총 메모리 사용량을 표시할지 말지
            # show_counts -> null이 아닌 값의 개수를 표시할지 말지,
            df.info()
            ```
        - unique : DataFrame 특정 컬럼의 고유값 확인
            ```python
            pd.unique(df["column명"])
            df["column명"].unique()
            ```
    - 속성
        - shape : DataFrame 형태 확인
            ```python
            df.shape # 메서드가 아니라 tuple 값을 가지는 attribute다.
            ```
        - columns : DataFrame을 이루는 Column 목록 확인
            ```python
            df.columns # 메서드가 아니라 list 값을 가지는 attribute다.
            ```
        - dtypes : DataFrame을 이루는 Column들의 타입 확인
            ```python
            df.dtypes
            ```
    - crosstab이란?
        ```
2. [matplotlib](https://matplotlib.org/)을 사용한 그래프 그리기
    - 그래프를 그리는데 두 가지 방식 존재 
        1. pyplot 방식
            ```python
            import matplotlib.pyplot as plt
            plt.plot(data)
            plt.show()
            ```
        2. 객체 지향 방식 (세부 조작 가능)
            ```python
            fig, ax = plt.subplots()
            ax.plot(data)
            plot.show()
            ```
    - 그래프 종류
        1. 선그래프
            ```python
            matplotlib.pyplot.plot(*args, scalex=True, scaley=True, data=None, **kwargs)
            ```
            - x,y : x생략시 자동으로 0,1,2 인덱스가 x축 값으로 설정된다.
            - color : 마커 색
                - b,g,r,c,m,y,k(검정),w가 있고 HEXCode로 주거나, 색상 이름, RGB 튜플값으로도 줄 수 있따.
            - linestyle : 라인 스타일
                - `-` : 실선 기본값, `--` : 파선, `-.` : 일점쇄선, `:` : 점선, `none`: 선 없음(마커만 표시)
            - linewidth : 선 두께(포인트 단위)
            - marker : 포인트 찍는거 모양
                - `o`:원, `s`:사각형, `^,v,<,>`: 삼각형, `*`: 별, `+,x,D`: 마름모, `.`:작은 점
            - 그 외 : [docs](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.plot.html) 참고
        2. 바그래프
            ```python
            matplotlib.pyplot.bar(x, height, width=0.8, bottom=None, *, align='center', data=None, **kwargs)
            ```
            - x : x축 데이터
            - height : y축 데이터 
            - width : 바의 두께
            - bottom : 막대가 시작하는 좌표 (default : 0)
            - 그 외  : [docs](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.bar.html)를 참고
        3. 산점도
            ```python
            matplotlib.pyplot.scatter(x, y, s=None, c=None, *, marker=None, cmap=None, norm=None, vmin=None, vmax=None, alpha=None, linewidths=None, edgecolors=None, colorizer=None, plotnonfinite=False, data=None, **kwargs)
            ```
            - x,y : x,y축 데이터
            - s,c : 마커의 크기, 색상
            - marker : 마커 모양 (default: o)
            - cmap : color map
            - vmin, vmax : color map이 적용되는 데이터 범위
            - 그외 : [docs](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.scatter.html) 참고
        4. 히스토그램
            ```python
            matplotlib.pyplot.hist(x, bins=None, *, range=None, density=False, weights=None, cumulative=False, bottom=None, histtype='bar', align='mid', orientation='vertical', rwidth=None, log=False, color=None, label=None, stacked=False, data=None, **kwargs)
            ```
            - 히스토그램 : x로 받은 데이터를 특정 구간별로 나누어, 구간에 포함되는 데이터의 개수를 확인시켜주는 그래프
            - x : 데이터
            - bins : 데이터를 나눌 구간의 개수 (int로 전달할 수도 있고,list로 직접 구간의 경계를 나눌 수도 있다. auto도 가능)
            - range : bins의 Upper/lower 범위 (벗어나는 이상치는 무시할 때 사용)
            - density : True일 경우, 확률밀도를 형성시키기 위해 정규화하여, 히스토그램 면적값은 1이 된다. (막대의 너비를 이용하여 정규화되므로 유의)
            - 그외 : [docs](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.hist.html) 참고
        5. 박스플롯
            ```python
            matplotlib.pyplot.boxplot(x, *, notch=None, sym=None, vert=None, orientation='vertical', whis=None, positions=None, widths=None, patch_artist=None, bootstrap=None, usermedians=None, conf_intervals=None, meanline=None, showmeans=None, showcaps=None, showbox=None, showfliers=None, boxprops=None, tick_labels=None, flierprops=None, medianprops=None, meanprops=None, capprops=None, whiskerprops=None, manage_ticks=True, autorange=False, zorder=None, capwidths=None, label=None, data=None)
            ```
            - 박스플롯 : 데이터의 분포를 5가지 요약 통계량으로 보여주는 그래프
                - 박스를 이용해서 Q1,Q2,Q3,IQR을 표현하고, 선으로 범위 내 극단값까지를 표현 (최대/최소 아님)
                    - 범위 : Q1-1.5IQR / Q3+1.5IQR
            - x : 데이터 (여러 개 입력도 가능)
            - tick_labels : 데이터 레이블 표시
            - showmeans : 평균 보여줄지 말지
            - notch : 중앙값 신뢰구간 홈 표시
            - vert : True면 세로 방향, False면 가로 방향
            - whis : 선 계수, 기본 1.5
            - 그 외 : [docs](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.boxplot.html)
        6. 히트맵
            ```python
            matplotlib.pyplot.imshow(X, cmap=None, norm=None, *, aspect=None, interpolation=None, alpha=None, vmin=None, vmax=None, colorizer=None, origin=None, extent=None, interpolation_stage=None, filternorm=True, filterrad=4.0, resample=None, url=None, data=None, **kwargs)
            ```
            - x : 데이터
            - cmap : colormap 어떤 색으로 표현할지
            - norm : 정규화
            - aspect : 종횡비 설정 (equal, auto)
                - equal : 1:1 (정사각형 출력)
                - auto : 축은 고정된 상태로 유지되고 데이터가 축에 맞도록 비율을 자동적으로 조정
            - 그 외 : [docs](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.imshow.html)
    - 그래프 꾸미기 설정
        - `fig,ax = plt.subplot()`을 사용한다는 가정
            1. 전체 제목 타이틀 설정
                ```python
                fig.suptitle("전체 캔버스 제목")
                ```
            2. x,y 레이블 설정
                ```python
                ax.set_xlabel("x축 레이블")
                ax.set_ylabel("y축 레이블")
                ```
            3. 개별 그래프 소제목 설정
                ```python
                ax.set_title("소제목 명")
                ```
        - `plt.figure()`를 사용한다는 설정
            1. 전체 제목 설정
                ```python
                plt.title("전체 제목명")
                ```
            2. x,y축 레이블 설정
                ```python
                plt.xlabel("x축 레이블")
                plt.ylabel("y축 레이블")
                ```
    - 한 캔버스에 여러 그래프 그리기
        - subplot을 사용하라
            ```python
            fig, axes = plt.subplots(행개수,열개수,figsize=(가로길이,세로길이)) 
            axes = axes.flatten() #axes가 2차원이기에 반복문 하나로 돌리기 어렵다. 1차원으로 변경해주는 함수
            ```
3. crosstab
    - crosstab은 두 변수 조합별 도수를 집계하는 표를 만드는 함수
    - 기본 사용법
        ```python
        import pandas as pd
        pd.crosstab(index,columns)
        ```
        - 행 : Index에 준 값
        - 열 : columns에 준 값
    - 주요 파라미터
        1. margins : 합계 행,열 추가
            ```python
            pd.crosstab(index,columns,margin=True,margins_name="합계")
            ```
            - 행/열 끝에 총합이 추가된다.
        2. normalize : 개수 대신 비율로 표기(총합:1)
            ```python
            pd.crosstab(index,columns, normalize=True)# 전체 합 :1
            pd.crosstab(index,columns, normalize='index') #각 행의 합 : 1
            pd.crosstab(index,columns, normalize='columns') #각 열의 합 : 1
            ```
        3. 인덱스나 Columns에 여러 개 전달해서 다중 표 제작 가능
            ```python
            pd.crosstab([index1,index2,...],columns)
            ```
        4. value, aggfunc : 빈도 대신 다른 집계
            - 빈도 대신 다른 값의 집계가 필요할 때 사용 가능
            ```python
            pd.crosstab(index,columns,values=value용column, aggfunc="mean/sum/count/,,,")
            ```
    - stack() : crosstab의 결과를 1차원으로 flat해주는 메서드
---
### 7월 2일
둘째 날로 이 날은 앞으로 계속 진행하게 될 코드스쿼드에서 진행했다.

작은 이슈로 내가 회사다닐때 습관이 있어서 일찍 가게 되었는데, 코드스쿼드에 아무도 없어서 계단에서 1시간을 기다렸다... 이제는 카드키 받아서 혼자서도 들어갈 수 있다.

코드스쿼드에서 첫날 규칙이나 사물함정하기 같은 OT를 진행했고, DA 수업이 진행되었다.

나는 소프티어에 붙고 나서 DE를 공부하다보니 아키텍처에 더 관심이 생겼다. 마침 이번에 DE와 별개로 DA도 뽑는다고 해서 둘 다 열심히 준비해보자는 생각을 했다.

DA 평가일은 7월 22일이라 시간이 별로 없는데, DB를 잘 모르기 때문에 주말에도 더 열심히 공부하고 해야겠다는 생각이 들었다.

이 날은 DA 수업 + 실습 + 미션 2(SQL)를 진행했었다.

#### DA 수업
1. 데이터 모델링 개요
    - 데이터 모델링이란?
        - 현실 세계의 업무를 **데이터를 담을 테이블 구조로 옮겨 그리는 설계** 작업
            - 즉, 코드 짜기 전 그리는 **서비스의 설계도**
            - **무엇(엔티티)** 을 **어떤 정보(속성)** 를 서로 **어떻게 연결(관계)할지**를 정하는 것
        - DB가 잘 동작하도록 만드는 구조
        - 즉, 테이블을 어떻게 나눌까 미리 설계하는 일
    - 모델링의 필요성
        1. 만드는 도중에 발생하는 예외로 인한 시간/비용 절약
            - 데이터가 쌓인 뒤에 구조를 바꾸면서 생기는 데이터 migration을 방지
        2. 애매한 부분을 미리 발견할 수 있다.
            - ex, 회원 한 명이 여러 주소를 가질 수 있나?
        3. 이해 관계자 모두가 같은 데이터 구조를 이해하고 대화 가능
        4. 잘못된 가정에서 오는 위험과 재작업 감소
        5. 빠른 의사결정, 빠른 가시화 가능
        > 즉, 나중에 고치기 어려우니까 먼저 그리는 것

    - 모델링이 빛나는 순간
        1. 신규 시스템 개발
            - 고민 : 가장 자유롭고 이상적으로 설계 가능
        2. 기존 시스템 변경
            - 고민 : 기존 구조와 충돌 안 나게, **영향 범위 파악**
        3. 전면 재구축
            - 고민 : 옛 데이터를 새 구조로 어떻게 옮길까
        > As-Is DB를 변경할 때 건드렸을 때 **어디가 깨지는지를 파악하는 것이 관건**이다.

    - 엔티티 / 속성 / 관계
        - 엔티티(Entity) : 업무가 다루는 어떤 것
            - 업무에서 **관리해야 하는 대상**
            - 하나의 엔티티가 **하나의 테이블**이 된다.
            - 엔티티 판단 기준 : 이것을 따로 저장하고 추적할 필요가 있는가?
                - 데이터는 **최소한으로 저장**하는 것이 가장 좋다. **WriteOnceReadNever**를 발생시키지 말자
        - 속성(Attribute) : Entity가 가지는 성격/정보
            - **엔티티가 가지는 세부 정보**로 **테이블의 Column**이 된다.
                - 이 Column명(속성명)을 **DB 메타데이터**라고 한다.
        - 관계(Relationship) : Entity 사이의 연결
            - 엔티티가 어떻게 엮이는지를 나타내는 것
            - 관계를 제대로 정하면, 데이터를 한 번에 추적할 수 있다. 
                - 반대로, 제대로 정하지 않으면 데이터 각각이 따로 놀게 된다.
    - 엔티티 타입과 인스턴스
        > 타입은 **공통 구조와 규칙**을 의미하고, 인스턴스는 **실제 데이터 1건**을 의미한다.

    - 모델 그리기
        > 개념 -> 논리 -> 물리로 해상도를 높여가며 진행
        >> 왜 나눠서 진행할까? : 각 단계의 관심사가 다르고, 큰 그림에서 합의해야 디테일 수정을 저렴하게 할 수 있다.
        1. 개념 모델
            > 목적 : 무엇을 다룰지 합의
            - 업무를 굵직한 덩어리로 보고, 세부 기술은 무시한다.
            - 기획자/현업자와 대화하며 그리는 단계다.
            - 데이터 타입 이런건 아직 신경 쓰지 않는다.
        2. 논리 모델
            > 목적 : DB에 독립적으로 업무 규칙을 정확히 표현
            - 개념 모델을 기반으로 **속성, 관계, 규칙을 명확히**
            - N:M 관계 풀어내기 작업 진행
        3. 물리 모델
            > 목적 : 실제로 구동되는 빠른 DB 만들기
            - 논리 모델을 특정 DBMS에 맞춰 구현
            - 테이블명/컬럼명 확정, 타입 지정
            - 인덱스, 제약조건, 성능 고려
            - 서비스는 대부분 DB가 느려져서 느려지는 것
                - slow query를 발견했을 때 대처
                    1. index 추가
                    2. SQL query 튜닝
                    3. schema 다시 설계
    - 데이터 관점의 업무 파악
        > 모델링을 위해서는 **무엇이 데이터로 남아야 하는지**를 골라야 한다.
        - 프로세스 : 일의 흐름을 파악한다.
            - ex, 주문 -> 결제 -> 배송 -> 완료
        - 데이터 관점 : 데이터의 생성,변화,저장 파악
            - **어떤 데이터가 남는가**를 파악
        
    - 데이터를 남기는 기준
        > 추적/분석할 필요가 있나?
        - 있으면 엔티티/속성, 없으면 과감히 제외하자.
            - 쓸데없는 데이터를 많이 저장하는 것은 무의미하다.
2. 엔티티와 속성
    - 엔티티란?
        > 우리가 테이블로 만들어서 저장하고 싶은 것
        - 업무에서 **관리**하거나 **처리**해야 하는 주요 대상
        - 공통된 특성으로 묶을 수 있는 **데이터의 집합**
        - 인스턴스의 집합
            - Entity : 인스턴스의 모임
                - **모임**이므로 1개만 존재하면 안 되고, 2개 이상 모일 수 있어야 한다.
    - 엔티티를 잡는 기준
        > 왜 이게 필요하지?를 계속 확인하자.
        >> 엔티티는 최소한으로 잡아야 한다.
        1. **업무에 필요**한가? : 시스템이 관리해야 할 정보인가?
        2. **여러 개 모이는가?** : 인스턴스가 2개 이상 생기는가?
        3. **식별이 되는가?** : 하나하나를 구별할 이름/번호가 있는가?
        4. **업무에서 실제로 사용되는가?** : 사용되지 않는 엔티티는 업무 분석이 잘못되었다는 신호다.
        5. **다른 엔티티와 연결되는가?** : 관계가 존재하는지 검증하는 것
            - 다만, 코드/통계성 데이터는 연결없이 두기도 한다.
    - 엔티티 분류
        > 실무에서는 매우 다양하게 분류한다. 이 부분은 책을 읽고 추가 정리하자.
        - 개체(키) 엔티티 : 그 자체로 존재하는 대상 
            - 명사
            - ex, 회원/상품/사원
        - 행위(내역) 엔티티 : 무언가 일어난 사건/행위
            - ~했다는 기록
            - ex, 주문, 결제, 로그인 이력
            - 행위 엔티티는 먼저 존재하던 개체 엔티티들이 만나서 생긴다.
    - 서브타입
        - 왜 필요할까?
            - 같은 엔티티인데 종류가 갈리는 경우, 공통은 슈퍼타입/차이는 서브타입으로 나눠서 관리한다.
                - 한 표에 모두 넣으면 NULL이 많아지기 떄문이다.
        - 애매해서 다 못나누겠다면, **기타** 구분을 만든다.
        - 슈퍼/서브는 부모-자식 관계랑 다르다. (같은 대상을 보는 관점일 뿐이다.)
        - 차이가 거의 없다면 그냥 속성 하나로 처리하는 것이 낫다.
    - 슈퍼타입 / 서브타입 구조
        ```text
                 회원 (슈퍼타입) — 공통 속성: 이름, 연락처
            ┌──────────┴──────────┐
        개인회원(서브)          법인회원(서브)
        생년월일                사업자번호
        ```
        > 서브타입끼리 겹치지 않고, 다 합치면 슈퍼타입과 1:1 대응
        - 슈퍼타입 : 공통 속성/관계를 보유
        - 서브타입 : 자기만의 속성을 추가로 가짐
    - 속성
        - 엔티티 안에서 **관리하고 싶은 정보 항목 하나하나**
            - 엔티티의 본질적인 성질
        - 속성도 결국 값들의 집합이다.
            - 데이터들의 집합
    - 좋은 속성의 조건
        1. 원자값 
            - 원자 단위(Atomic): 더 쪼개면 의미가 깨지는 가장 작은 단위
            - 원칙 : 일단 최소 단위로 쪼개고, 필요에 따라 합친다.
                - 너무 쪼개도, 안 쪼개도 문제다. 따라서 **업무 요구 사항**에 따라 결정하자.
        2. 단일값
            - **하나의 인스턴스**에 대해 그 **속성은 값을 딱 하나**만 가져야 한다.
            - 반복되는 값이 있다면, 별도 엔티티로 분리하자.
            - 판단의 핵심은 결국 **왜**를 묻는 것이다.
                - ex, 전화번호가 여러 개인 상황
                    - 대표 전화 하나만 관리 -> 속성 하나
                    - 모든 연락처 관리 -> 별도 엔티티 분리 필요
                - 정의에 따라 모델이 달라진다.
    - 속성 검증 4단계
        1. 최소 단위 분할 : 원자 단위 분할
        2. 유일값 검증 : 값이 하나인지 파악, 반복되면 분리
        3. 가공값 판정 : 계산으로 다시 만들 수 있는 값인가?
            - 합계나 나이처럼 다시 만들 수 있다면 보통 생략
                - 근데 생략 안하는 경우도 있고, Redis같은 인메모리 DB에 저장해서 집계 처리하는 경우도 있다.
                - 이건 논리 단계에서 생각하는게 아니다. 물리 단계에서 생각
        4. 관리수준 검토 : 더 상세히 관리할 필요가 있나?
    - 필수 / 선택 속성
        - Nullable과 Non-Nullable 구분
            - 업무 규칙으로 결정한다.
    - 데이터 시뮬레이션
        - 가장 저렴한 검증 방법 : 실제 샘플 데이터를 넣어보는 것
        - 논리 모델 개발 후, 테이블에 샘플 데이터를 몇 줄 넣어보기
            - 이 과정에서 **모델의 오류**나 **오해**를 알 수 있다.
        - 장점 
            1. 가장 적은 비용으로 모델 검증 가능
            2. 개발자, 모델러, 기획자 사이의 의사소통 오류 파악 가능
            3. 특수 케이스(예외)를 미리 발견 가능
                - 이를 위해, 꼼꼼히 작성할 수록 좋다.
            4. 만든 샘플은 나중에 **테스트 데이터**로도 재사용 가능하다.
                - 만들 때 AI를 쓰는 것도 좋은데, 그냥 쓰지말고 아래처럼 Prompt Tuning을 잘해보자.
                    - "현실 세계의 통계,분포,조건을 고려하여 생성해달라"
                - 직접 데이터를 만들어낼 수 있는 프로그램을 개발하는 것도 괜찮다.
                    - 도메인 지식을 잘 아는 사람이 프로그램으로 만들어서 쓰면 시뮬레이션이 더 잘 된다.
3. 관계와 ERD
    - 관계란?
        - 엔티티 사이의 **업무적 연관성**
        - 단순한 연결선이 아닌 업무 규픽을 담는다.
            - 고객은 주문을 한다. / 주문은 상품을 포함한다. ...
        - 참조 무결성을 지켜주는 핵심 장치다.
            - 참조 무결성
                - DB에서 관련된 두 테이블 간의 데이터 일관성을 유지하기 위한 규칙
                    - 한 테이블의 FK가 다른 테이블의 PK를 참조할 때, 존재하지 않는 데이터를 가리키거나 엉키지 않도록 보호하는 역할
            - '존재하지 않는 고객의 주문은 만들 수 없다'와 같은
            - 이로 인해, 성능 저하가 미약하게 발생한다.
                - 매번 PK가 있는지 확인해야 하므로
                - But, PK는 기본 인덱스를 가지므로 심히 느려지지는 않는다.
                    - PK 인덱스는 B+트리로 O(logN)의 성능인데, log의 밑은 1000이상이다. (페이지 단위로 관리하기 때문)
    - 기수성(Cardinality)
        - **한 엔티티의 인스턴스 하나**가 **상대 인스턴스를 몇 개** 가질 수 있는가?
        - 대부분 실무 관계는 1:N으로 정리된다.
            - 1:1은 사실 같은 엔티티일 가능성이 높다. (즉 합칠 수 있다.)
                - 굳이 나눌 이유가 존재할 때만 분리하자. (자주 사용하지 않는 큰 컬럼 분리, 접근 권한 분리 등)
        - 1:N 관계
            - 가장 일반적인 관계다.
        - M:N 관계는 Application 설계 관점에서도 좋지 않기에 분리한다.
            - 또한, 관계형 DB는 M:N을 직접 표현할 수 없다. (FK하나로 양쪽을 다 가리킬 수 없기 때문이다.)
                - 따라서, 교차 엔티티(중간 테이블)로 1:N 2개로 풀어줘야 한다.
            - 언제 풀까?
                > 복잡성에 빠지지말자, 필요하면 교차엔티티로 쉽게 풀자
                1. 관계 자체에 속성을 채워야 하는 경우
                    - ex, 주문 수량, 신청일 등
                2. 관계가 또 다른 자식 엔티티가 필요한 경우
                3. 관계명을 붙이기 어렵다면, 추가 엔티티가 필요하다는 뜻
    - 선택성
        - 관계가 반드시 있어야 하는가, 아니면 없을 수도 있는가?
            - 필수 : 무조건 짝이 존재해야 함
            - 선택 : 짝이 없어도 된다. 
        - 기수성과 선택성은 양 방향으로 따로 본다.
    - 양 방향에서 관계 보기
        - ex, 고객과 주문이라면, 
            - 고객 입장에서는 한 고객은 0개 이상의 주문을 가질 수 있다. (선택적, N을 가짐)
            - 주문 입장에서는 한 주문은 한 명의 고객에게 반드시 속한다. (필수적, 1과 대응)
    - 관계 속성
        > **두 엔티티에 관계가 있다**는 것은 **PK를 FK로 물려받는다**는 의미
        - 관계는 코드 레벨에서 외래키 컬럼으로 구현된다.
    - 식별 / 비식별 관계
        - 식별 관계
            - FK가 PK의 일부가 된다. 
                - 즉, 부모 테이블에 연결되지 않는 자식 레코드가 존재할 수 없다.
            - 까마귀발 표기법으로 실선으로 표시한다.
        - 비식별 관계
            - FK와 별도로 PK를 가진다. (대부분 인공키)
                - 즉, FK가 NULL인 자식 레코드가 존재할 수 있다.
            - 까마귀발 표기법으로 점선으로 표시한다.
    - 다중 관계 해소 (두 엔티티가 여러 번 얽히는 경우)
        - ex, 주문할 때 주문자, 수령자 2개 필요
        - 해소 방법
            1. **병렬식** : FK 컬럼을 여러 개 늘린다.
                - 종류가 고정되어있고, 소수일 때 선택
            2. **직렬식** : 관계 엔티티를 따로 둔다.
                - 종류가 늘어날 여지가 있고, 이력이 필요한 경우 선택
    - 첸 표기법
        - 정리 필요
#### SQL 정리