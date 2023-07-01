#region imports
from AlgorithmImports import *
#endregion
class PriceEarningsAnamoly(QCAlgorithm):

    def Initialize(self):

        self.SetStartDate(2020, 5, 1)   
        self.SetEndDate(2022, 8, 22)         
        
        self.InitCash = 50000
        self.SetCash(self.InitCash)
        
        self.MKT = self.AddEquity("SPY", Resolution.Daily).Symbol
        self.SetBenchmark("SPY")
        self.mkt = []
        
        self.UniverseSettings.Resolution = Resolution.Daily
        self.symbols = []
        
        
        # record the year that have passed since the algorithm starts
        self.year = -1
        self._NumCoarseStocks = 150
        self._NumStocksInPortfolio = 20
        
        self.AddUniverse(self.CoarseSelectionFunction, self.FineSelectionFunction)
        self.averages = {}
        
        #self.SetRiskManagement(MaximumDrawdownPercentPerSecurityCustom(.45))
        
        
    def OnEndOfDay(self):  
        mkt_price = self.History(self.MKT, 2, Resolution.Daily)['close'].unstack(level= 0).iloc[-1]
        self.mkt.append(mkt_price)
        mkt_perf = self.InitCash * self.mkt[-1] / self.mkt[0] 
        self.Plot('Strategy Equity', self.MKT, mkt_perf)
        
    def CoarseSelectionFunction(self, coarse):
        selected = []
        if self.Time.year == self.year:
            return self.symbols
        
        # drop stocks which have no fundamental data or have low price
        
        CoarseWithFundamental = [x for x in coarse if x.HasFundamentalData and x.Price > 50]
        sortedByDollarVolume = sorted(CoarseWithFundamental, key=lambda x: x.DollarVolume, reverse=False) 
        
        for coarse in sortedByDollarVolume:
            symbol = coarse.Symbol
            
            if symbol not in self.averages:
                history = self.History(symbol, 100, Resolution.Daily)
                self.averages[symbol] = SelectionData(history)
                
            self.averages[symbol].update(self.Time, coarse.AdjustedPrice) 
            
            if self.averages[symbol].fast > self.averages[symbol].slow:
                if self.averages[symbol].slow.IsReady and self.averages[symbol].fast.IsReady :
                    selected.append(symbol)
        
        return selected

    def FineSelectionFunction(self, fine):
        
        if self.Time.year == self.year:
            return self.symbols
        
        self.year = self.Time.year
        
        
        fine = [x for x in fine if x.ValuationRatios.PBRatio > 0 ]
        
        filterSector = [x for x in fine if x.AssetClassification.MorningstarSectorCode == MorningstarSectorCode.Technology]
        
        sortedPBRatio = sorted(filterSector, key=lambda x: x.ValuationRatios.PBRatio)
        PBRatioPicks = [i for i in sortedPBRatio[:self._NumStocksInPortfolio*2]]
        
        sortedPCFRatio = sorted(filterSector, key=lambda x: x.ValuationRatios.PCFRatio)
        PCFRatioPicks = [i for i in sortedPCFRatio[:self._NumStocksInPortfolio*2]]
        
        sumRatio = PBRatioPicks + PCFRatioPicks
        sortedEV_EBITDA = sorted(sumRatio, key=lambda x: x.ValuationRatios.EVToEBITDA)
        
        GrowthPicks = [i for i in sortedEV_EBITDA[:self._NumStocksInPortfolio*2]]
        
        sortedMomentum = sorted(GrowthPicks, key=lambda x: x.ValuationRatios.PriceChange1M)
        
        self.symbols = [i.Symbol for i in sortedMomentum[:self._NumStocksInPortfolio]]
        
        return self.symbols
    
    def OnSecuritiesChanged(self, change):
        
        # liquidate securities that removed from the universe
        for security in change.RemovedSecurities:
            if self.Portfolio[security.Symbol].Invested:
                self.Liquidate(security.Symbol)

        count = len(change.AddedSecurities)

        # evenly invest on securities that newly added to the universe
        for security in change.AddedSecurities:
            self.SetHoldings(security.Symbol, 1.0/count)
            
        
class SelectionData():
    def __init__(self, history):
        self.slow = ExponentialMovingAverage(100) 
        self.fast = ExponentialMovingAverage(50) 
        
        for bar in history.itertuples():
            self.fast.Update(bar.Index[1], bar.close)
            self.slow.Update(bar.Index[1], bar.close)
        
    def is_ready():
        return self.slow.IsReady and self.fast.IsReady
    
    def update(self, time, price):
        self.fast.Update(time, price)
        self.slow.Update(time, price)
        
class MaximumDrawdownPercentPerSecurityCustom(RiskManagementModel):

    def __init__(self, maximumDrawdownPercent = 0.01):
        self.maximumDrawdownPercent = -abs(maximumDrawdownPercent)
        self.liquidated = set()
        self.currentTargets = set()

    def ManageRisk(self, algorithm, targets):
        # Reset liquidated symbols on new targets
        #algorithm.Log(targets[0].Quantity)
        
        if set(targets) != self.currentTargets:
            #algorithm.Log("Different")
            self.currentTargets = set(targets)
            self.liquidated = set()
        
        targets = []
        for kvp in algorithm.Securities:
            security = kvp.Value

            pnl = security.Holdings.UnrealizedProfitPercent
            if pnl < self.maximumDrawdownPercent or security.Symbol in self.liquidated:
                # liquidate
                targets.append(PortfolioTarget(security.Symbol, 0))
                if algorithm.Securities[security.Symbol].Invested:
                    self.liquidated.add(security.Symbol)
                    #algorithm.Log(f"Liquidating {security.Symbol}")

        return targets
