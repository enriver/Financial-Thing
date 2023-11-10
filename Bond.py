from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd

pd.options.display.float_format = '{:.2f}'.format


# 거듭제곱
def power(a,b):
    return a**b

# 각 채권의 정보를 담기 위해 채권 클래스 생성
class Bond:
    
    def __init__(self, faceValue, iRate, iPaymentWay, iPaymentPeriod, dateOfIssue, dateOfMaturity):

        self.faceValue = faceValue # 액면가
        self.bookValue = faceValue # 장부가 (초기값 액면값으로 설정)
        self.iRate = iRate/100 # 발행이율
        self.iPaymentWay = iPaymentWay # 이자지급방법 (복리채, 단리채, 이표채, 할인채 등)
        self.iPaymentPeriod = iPaymentPeriod # 이자지급주기 (연지급, 반기지급, 분기지급, 월지급 등)
        self.dateOfIssue = datetime.strptime(dateOfIssue,'%Y%m%d') # 발행일
        self.dateOfMaturity = datetime.strptime(dateOfMaturity,'%Y%m%d') # 만기일

        self.calcCouponRate()
        self.makeCashFlow('F')

    def calcCouponRate(self):
        match self.iPaymentPeriod:
            case 12 : # 연지급
                self.cRate = self.iRate
            case 6 : # 반기 지급
                self.cRate = self.iRate / 2
            case 3 : # 분기 지급
                self.cRate = self.iRate / 4
            case 1 : # 월별 지급
                self.cRate = self.iRate / 12
            case _ :
                raise Exception("Wrong iPaymentPeriod parameter is input !!")


    # 이자 및 상환액 전체에 대한 cashflow 생성
    def makeCashFlow(self, flag):

        # 이자지급방법에 따른 cashflow 생성
        match self.iPaymentWay :
            case '1':
                print('복리채')
            case '2':
                print('단리채')
            case '3': # 이표채
                self.makeCouponBondCF(flag)
            case '5':
                print('복5단2')
            case '_':
                raise Exception('Wrong iPaymentWay parameter is input !!')

        self.calcIRR()
            
    def showInfo(self):
        print('[faceValue] ='     , self.faceValue,
            '\n[iRate] ='         , self.iRate,
            '\n[iPaymentWay] ='   , self.iPaymentWay,
            '\n[iPaymentPeriod] =', self.iPaymentPeriod,
            '\n[dateOfIssue] ='   , self.dateOfIssue,
            '\n[dateOfMaturity] =', self.dateOfMaturity)


    def purchase(self, bookValue, dateOfPurchase):
        self.bookValue=bookValue # 장부가
        self.dateOfPurchase = datetime.strptime(dateOfPurchase,'%Y%m%d') # 매입일

        if self.dateOfIssue != self.dateOfPurchase :
            self.makeCashFlow('R')
    

    def makeCouponBondCF(self,flag):
        if flag=='F': # 발행일자 기준 CF 계산 (채권 정보등록 시 최초 시행)
            
            tmpList=list()
            cfEnd = self.dateOfIssue
            while True:
                if cfEnd == self.dateOfMaturity:
                    break
                
                # CF계산 시작일, CF계산 종료일
                cfStart = cfEnd
                cfEnd += relativedelta(months = self.iPaymentPeriod)

                # CF발생기간(일수), 예상 현금흐름액(CF)
                cfDiffDays = cfEnd - cfStart
                cfAmount = self.faceValue*self.cRate

                tmpList.append([cfStart,cfEnd,cfDiffDays,1,cfAmount,cfAmount])

            self.cashFlow = pd.DataFrame(tmpList, columns=['CF_StartDate','CF_EndDate','CF_Period','Weighted_R','CF_E_Amount', 'CF_R_Amount'])

        elif flag=='R' : # 채권 매입일자 기준 CF 계산
            print('**** CF 재계산 ****')

            idx=0
            size=len(self.cashFlow)

            newCf=list()
            while True:
                if idx == size:
                    break
                
                # CF계산 종료일이 매입일 이전이라면, 실제 발생 현금흐름 -> 0
                if self.dateOfPurchase >= self.cashFlow.loc[idx,'CF_EndDate'] :
                    self.cashFlow.loc[idx, 'CF_R_Amount'] = 0

                # 매입일이 CF계산 종료일 이전일 경우
                else:

                    # 만약 CF계산 시작일과 매입일이 동일하다면, 새로운 현금흐름을 생성하지 않고 반복 종료
                    if self.dateOfPurchase == self.cashFlow.loc[idx,'CF_StartDate']:
                        break

                    # CF계산 시작일~매입일  구간  현금흐름 생성
                    diffDay1 = self.dateOfPurchase - self.cashFlow.loc[idx,'CF_StartDate']
                    newCf.extend([
                          self.cashFlow.loc[idx,'CF_StartDate']
                        , self.dateOfPurchase
                        , diffDay1
                        , diffDay1/self.cashFlow.loc[idx,'CF_Period']
                        , self.cashFlow.loc[idx, 'CF_E_Amount']
                        , self.cashFlow.loc[idx,'CF_E_Amount']*(diffDay1 / self.cashFlow.loc[idx,'CF_Period'])
                    ])

                    # 매입일~CF계산 종료일 구간 현금흐름 수정
                    self.cashFlow.loc[idx,'CF_StartDate']=self.dateOfPurchase

                    diffDay2 = self.cashFlow.loc[idx,'CF_EndDate'] - self.dateOfPurchase
                    self.cashFlow.loc[idx,'Weighted_R'] = diffDay2/self.cashFlow.loc[idx,'CF_Period']

                    self.cashFlow.loc[idx,'CF_R_Amount']=self.cashFlow.loc[idx,'CF_E_Amount']*self.cashFlow.loc[idx,'Weighted_R']
                    self.cashFlow.loc[idx,'CF_Period'] = diffDay2

                    break

                idx+=1

            # 새로운 현금흐름을 작성하는 경우 (매입일 != CF계산 시작일)
            if newCf:
                self.cashFlow.loc[size]=newCf
                
            self.cashFlow.sort_values(by='CF_StartDate', ignore_index=True, inplace=True)

    # 내부수익률 Internal Rate of Return 계산
    # 장부가==sum(발생CF/(1+i)^n) ?  i 확정 : i 수정
    def calcIRR(self):
        REPEAT = 200       # 반복시행 횟수
        tmpRate=self.cRate # 임의의 내부수익률 설정
        correctionR = 0.5  # 수정치
        flag = 1          

        for _ in range(REPEAT):
            tmpAmt = 0

            # 미래에 예정되어있는 현금흐름을
            # 채권 매입일자로 할인
            size = len(self.cashFlow)
            for i in range(size):
                if self.cashFlow['CF_R_Amount'][i] == 0: # 현금흐름이 있는 경우만 고려
                    continue

                eAmount = self.cashFlow['CF_E_Amount'][i]

                if i == size-1 : # 마지막 현금흐름에 액면가를 더함
                    eAmount+=self.faceValue

                tmpAmt+=eAmount/power(1+tmpRate,sum(self.cashFlow['Weighted_R'][:i+1]))

            # 장부가격(매입가격) 과 비교
            if abs(tmpAmt-self.bookValue) < 0.001 : # 그 차이가 근소할 때
                break


            ## 내부수익률 수정 구간 ##
            # 이전 계산 결과를 flag 를 통해 확인
            if flag == 1:
                # 계산한 금액이 장부가격 보다 큰 경우
                if (tmpAmt - self.bookValue) > 0 :
                    flag = -1    
                    correctionR*=-0.5 # 수정치 재계산

            else:
                # 계산한 금액이 장부가격보다 작은 경우    
                if (tmpAmt - self.bookValue) < 0 :
                    flag = 1
                    correctionR*=-0.5
                
            tmpRate+=correctionR # 내부수익률 수정

        # 내부수익률 확정
        self.IRR = tmpRate*(12/self.iPaymentPeriod)





if __name__=="__main__" :
    faceValue = 10_000_000_000 # 액면가 -> 100억
    iRate = 3.8 # 표면이율 -> 3.8
    iPaymentWay = '3' # 이표채
    iPaymentPeriod = 3 # 분기별 지급
    dateOfIssue = '20190101' # 채권 발행일
    dateOfMaturity = '20240101' # 채권 만기일

    bd = Bond(faceValue,iRate,iPaymentWay,iPaymentPeriod,dateOfIssue,dateOfMaturity)
    bd.showInfo()
    print()


    ## BondHolder 클래스를 만들어 진행해야 하나, 편의를 위해 그냥 TEST함


    # CASE 1 발행일과 매입일이 일치하는 경우
    bookValue = 9_000_000_000 # 장부가
    dateOfPurchase = '20190101' # 매입일
    bd.purchase(bookValue, dateOfPurchase) # 채권 매입
    print('[CASE 1]\n==========')
    print('CASH FLOW')
    print(bd.cashFlow)
    print('\nInternal Rate of Return')
    print(bd.IRR)
    print()


    # CASE 2  발행일과 매입일이 일치하지 않는 경우
    bookValue = 9_000_000_000 # 장부가
    dateOfPurchase = '20200201' # 매입일
    bd.purchase(bookValue, dateOfPurchase) # 채권 매입
    print('[CASE 2]\n==========')
    print('CASH FLOW')
    print(bd.cashFlow)
    print('\nInternal Rate of Return')
    print(bd.IRR)
