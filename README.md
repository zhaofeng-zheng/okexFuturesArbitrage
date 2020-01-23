# okexFuturesArbitrage
Warning:
  Please make sure you fully understand how futures contracts at OKEx works before using this programme.
  You can learn about it at OKEx (https://okexsupport.zendesk.com/hc/zh-cn/articles/360000104591-%E5%90%88%E7%BA%A6%E8%B4%A6%E6%88%B7%E5%8F%8A%E7%9B%88%E4%BA%8F%E8%AE%A1%E7%AE%97)

Brief
  This is a simple arbitrage programmme that is based on coin margined futures at OKEx.

Description
  The price difference between weekly and quaterly coin margined futures oscillates between a certain range at all times (e.g. 1.5 % to     3.0%) and price difference above this range occurs only rarely if at all. This simple python programme exploits the assumption that when price difference deviates significantly from its normal range, it must fall back. This is because unlikely prices of the underlyings(BTC, ETH), the price difference does not form a trend due to the very nature that futures price always revolve around the price of the underlying.
  数字货币期货合约当周和季度价差永远在一个范围内波动， 极少产生趋势。 这个简单python程序利用这个特点， 结合网格交易法则， 实现了多账户期货套利。

