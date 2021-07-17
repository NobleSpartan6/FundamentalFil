class PriceSalePriceBook(QCAlgorithm):

    def Initialize(self):
        '''Initialise the data and resolution required, as well as the cash and start-end dates for your algorithm. All algorithms must initialized.'''

        self.SetStartDate(2016,1,1)  #Set Start Date
        self.SetEndDate(2019,7,1)    #Set End Date
        self.SetCash(100000)         #Set Strategy Cash
        self.SetBenchmark("SPY")     #Set Benchmark   

        self.UniverseSettings.Resolution = Resolution.Daily
        self.symbols = []

        self.AddUniverse(self.CoarseSelectionFunction, self.FineSelectionFunction)
        
        # record the years passed since the algorithm starts
        self.year = -1
        self._NumCoarseStocks = 200
        self._NumStocksInPortfolio = 10


    # sort the data by daily dollar volume and take the top 'NumberOfSymbols'
    def CoarseSelectionFunction(self, coarse):
        
        if self.Time.year == self.year:
            return self.symbols
            
        # Keep stocks with fundamental data and price greater than 5
        CoarseWithFundamental = [x for x in coarse if x.HasFundamentalData and x.Price > 5]
        
        # sort by daily dollar volume
        sortedByDollarVolume = sorted(CoarseWithFundamental, key=lambda x: x.DollarVolume, reverse=False)

        # return the symbol objects of the top entries from our sorted collection
        return [x.Symbol for x in sortedByDollarVolume[:self._NumCoarseStocks]]
        
    def FineSelectionFunction(self, fine):
        
        if self.Time.year == self.year:
            return self.symbols
            
        self.year = self.Time.year
            
        fine = [x for x in fine if x.ValuationRatios.PSRatio > 0]
        filterSector = [x for x in fine if x.AssetClassification.MorningstarSectorCode == MorningstarSectorCode.Technology]
        sortedPSRatio = sorted(filterSector, key=lambda x: x.ValuationRatios.PSRatio)
        sortedPBRatio = sorted(filterSector, key=lambda x: x.ValuationRatios.PBRatio)
        self.symbols = [i.Symbol for i in sortedPBRatio[:self._NumStocksInPortfolio]]
        
        return self.symbols

    # this event fires whenever we have changes to our universe
    def OnSecuritiesChanged(self, change):
        
        # liquidate securities that removed from the universe
        for security in change.RemovedSecurities:
            if self.Portfolio[security.Symbol].Invested:
                self.Liquidate(security.Symbol)

        count = len(change.AddedSecurities)

        # evenly invest on securities that newly added to the universe
        for security in change.AddedSecurities:
            self.SetHoldings(security.Symbol, 1.0/count)
