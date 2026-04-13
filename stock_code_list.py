#!/usr/bin/env python3
"""
常用A股股票代码列表
用于Tushare无权限时的备用搜索
"""

# 沪深300成分股（部分常用股票）
STOCK_LIST = [
    # 金融
    {"ts_code": "000001.SZ", "symbol": "000001", "name": "平安银行", "industry": "银行"},
    {"ts_code": "000002.SZ", "symbol": "000002", "name": "万科A", "industry": "房地产"},
    {"ts_code": "600000.SH", "symbol": "600000", "name": "浦发银行", "industry": "银行"},
    {"ts_code": "600016.SH", "symbol": "600016", "name": "民生银行", "industry": "银行"},
    {"ts_code": "600028.SH", "symbol": "600028", "name": "中国石化", "industry": "石油石化"},
    {"ts_code": "600030.SH", "symbol": "600030", "name": "中信证券", "industry": "证券"},
    {"ts_code": "600036.SH", "symbol": "600036", "name": "招商银行", "industry": "银行"},
    {"ts_code": "600048.SH", "symbol": "600048", "name": "保利发展", "industry": "房地产"},
    {"ts_code": "601318.SH", "symbol": "601318", "name": "中国平安", "industry": "保险"},
    {"ts_code": "601398.SH", "symbol": "601398", "name": "工商银行", "industry": "银行"},
    {"ts_code": "601628.SH", "symbol": "601628", "name": "中国人寿", "industry": "保险"},
    {"ts_code": "601888.SH", "symbol": "601888", "name": "中国中免", "industry": "旅游"},

    # 消费
    {"ts_code": "000568.SZ", "symbol": "000568", "name": "泸州老窖", "industry": "白酒"},
    {"ts_code": "000596.SZ", "symbol": "000596", "name": "古井贡酒", "industry": "白酒"},
    {"ts_code": "000651.SZ", "symbol": "000651", "name": "格力电器", "industry": "家电"},
    {"ts_code": "000725.SZ", "symbol": "000725", "name": "京东方A", "industry": "面板"},
    {"ts_code": "000768.SZ", "symbol": "000768", "name": "中航西飞", "industry": "航空"},
    {"ts_code": "000858.SZ", "symbol": "000858", "name": "五粮液", "industry": "白酒"},
    {"ts_code": "000895.SZ", "symbol": "000895", "name": "双汇发展", "industry": "食品"},
    {"ts_code": "002001.SZ", "symbol": "002001", "name": "新和成", "industry": "化工"},
    {"ts_code": "002007.SZ", "symbol": "002007", "name": "华兰生物", "industry": "医药"},
    {"ts_code": "002024.SZ", "symbol": "002024", "name": "苏宁易购", "industry": "零售"},
    {"ts_code": "002027.SZ", "symbol": "002027", "name": "分众传媒", "industry": "传媒"},
    {"ts_code": "002049.SZ", "symbol": "002049", "name": "紫光国微", "industry": "半导体"},
    {"ts_code": "002120.SZ", "symbol": "002120", "name": "韵达股份", "industry": "物流"},
    {"ts_code": "002142.SZ", "symbol": "002142", "name": "宁波银行", "industry": "银行"},
    {"ts_code": "002230.SZ", "symbol": "002230", "name": "科大讯飞", "industry": "人工智能"},
    {"ts_code": "002271.SZ", "symbol": "002271", "name": "东方雨虹", "industry": "建材"},
    {"ts_code": "002304.SZ", "symbol": "002304", "name": "洋河股份", "industry": "白酒"},
    {"ts_code": "002352.SZ", "symbol": "002352", "name": "顺丰控股", "industry": "物流"},
    {"ts_code": "002415.SZ", "symbol": "002415", "name": "海康威视", "industry": "安防"},
    {"ts_code": "002460.SZ", "symbol": "002460", "name": "赣锋锂业", "industry": "锂电池"},
    {"ts_code": "002475.SZ", "symbol": "002475", "name": "立讯精密", "industry": "电子"},
    {"ts_code": "002594.SZ", "symbol": "002594", "name": "比亚迪", "industry": "汽车"},
    {"ts_code": "002714.SZ", "symbol": "002714", "name": "牧原股份", "industry": "养殖"},
    {"ts_code": "002812.SZ", "symbol": "002812", "name": "恩捷股份", "industry": "锂电池"},
    {"ts_code": "003816.SZ", "symbol": "003816", "name": "中国广核", "industry": "电力"},

    # 医药
    {"ts_code": "300003.SZ", "symbol": "300003", "name": "乐普医疗", "industry": "医疗器械"},
    {"ts_code": "300014.SZ", "symbol": "300014", "name": "亿纬锂能", "industry": "锂电池"},
    {"ts_code": "300015.SZ", "symbol": "300015", "name": "爱尔眼科", "industry": "医疗服务"},
    {"ts_code": "300033.SZ", "symbol": "300033", "name": "同花顺", "industry": "金融软件"},
    {"ts_code": "300059.SZ", "symbol": "300059", "name": "东方财富", "industry": "互联网金融"},
    {"ts_code": "300122.SZ", "symbol": "300122", "name": "智飞生物", "industry": "疫苗"},
    {"ts_code": "300124.SZ", "symbol": "300124", "name": "汇川技术", "industry": "工业自动化"},
    {"ts_code": "300142.SZ", "symbol": "300142", "name": "沃森生物", "industry": "疫苗"},
    {"ts_code": "300274.SZ", "symbol": "300274", "name": "阳光电源", "industry": "光伏"},
    {"ts_code": "300408.SZ", "symbol": "300408", "name": "三环集团", "industry": "电子"},
    {"ts_code": "300413.SZ", "symbol": "300413", "name": "芒果超媒", "industry": "传媒"},
    {"ts_code": "300433.SZ", "symbol": "300433", "name": "蓝思科技", "industry": "电子"},
    {"ts_code": "300498.SZ", "symbol": "300498", "name": "温氏股份", "industry": "养殖"},
    {"ts_code": "300750.SZ", "symbol": "300750", "name": "宁德时代", "industry": "锂电池"},
    {"ts_code": "300760.SZ", "symbol": "300760", "name": "迈瑞医疗", "industry": "医疗器械"},
    {"ts_code": "300999.SZ", "symbol": "300999", "name": "金龙鱼", "industry": "食品"},

    # 科技
    {"ts_code": "600009.SH", "symbol": "600009", "name": "上海机场", "industry": "机场"},
    {"ts_code": "600019.SH", "symbol": "600019", "name": "宝钢股份", "industry": "钢铁"},
    {"ts_code": "600031.SH", "symbol": "600031", "name": "三一重工", "industry": "工程机械"},
    {"ts_code": "600104.SH", "symbol": "600104", "name": "上汽集团", "industry": "汽车"},
    {"ts_code": "600276.SH", "symbol": "600276", "name": "恒瑞医药", "industry": "医药"},
    {"ts_code": "600309.SH", "symbol": "600309", "name": "万华化学", "industry": "化工"},
    {"ts_code": "600406.SH", "symbol": "600406", "name": "国电南瑞", "industry": "电力设备"},
    {"ts_code": "600436.SH", "symbol": "600436", "name": "片仔癀", "industry": "中药"},
    {"ts_code": "600438.SH", "symbol": "600438", "name": "通威股份", "industry": "光伏"},
    {"ts_code": "600519.SH", "symbol": "600519", "name": "贵州茅台", "industry": "白酒"},
    {"ts_code": "600585.SH", "symbol": "600585", "name": "海螺水泥", "industry": "水泥"},
    {"ts_code": "600690.SH", "symbol": "600690", "name": "海尔智家", "industry": "家电"},
    {"ts_code": "600745.SH", "symbol": "600745", "name": "闻泰科技", "industry": "半导体"},
    {"ts_code": "600809.SH", "symbol": "600809", "name": "山西汾酒", "industry": "白酒"},
    {"ts_code": "600887.SH", "symbol": "600887", "name": "伊利股份", "industry": "乳制品"},
    {"ts_code": "600900.SH", "symbol": "600900", "name": "长江电力", "industry": "水电"},
    {"ts_code": "601012.SH", "symbol": "601012", "name": "隆基绿能", "industry": "光伏"},
    {"ts_code": "601066.SH", "symbol": "601066", "name": "中信建投", "industry": "证券"},
    {"ts_code": "601088.SH", "symbol": "601088", "name": "中国神华", "industry": "煤炭"},
    {"ts_code": "601100.SH", "symbol": "601100", "name": "恒立液压", "industry": "液压"},
    {"ts_code": "601111.SH", "symbol": "601111", "name": "中国国航", "industry": "航空"},
    {"ts_code": "601138.SH", "symbol": "601138", "name": "工业富联", "industry": "电子"},
    {"ts_code": "601166.SH", "symbol": "601166", "name": "兴业银行", "industry": "银行"},
    {"ts_code": "601211.SH", "symbol": "601211", "name": "国泰君安", "industry": "证券"},
    {"ts_code": "601288.SH", "symbol": "601288", "name": "农业银行", "industry": "银行"},
    {"ts_code": "601318.SH", "symbol": "601318", "name": "中国平安", "industry": "保险"},
    {"ts_code": "601336.SH", "symbol": "601336", "name": "新华保险", "industry": "保险"},
    {"ts_code": "601390.SH", "symbol": "601390", "name": "中国中铁", "industry": "建筑"},
    {"ts_code": "601668.SH", "symbol": "601668", "name": "中国建筑", "industry": "建筑"},
    {"ts_code": "601688.SH", "symbol": "601688", "name": "华泰证券", "industry": "证券"},
    {"ts_code": "601818.SH", "symbol": "601818", "name": "光大银行", "industry": "银行"},
    {"ts_code": "601857.SH", "symbol": "601857", "name": "中国石油", "industry": "石油"},
    {"ts_code": "601888.SH", "symbol": "601888", "name": "中国中免", "industry": "免税"},
    {"ts_code": "601933.SH", "symbol": "601933", "name": "永辉超市", "industry": "零售"},
    {"ts_code": "601995.SH", "symbol": "601995", "name": "中金公司", "industry": "证券"},
    {"ts_code": "603288.SH", "symbol": "603288", "name": "海天味业", "industry": "食品"},
    {"ts_code": "603501.SH", "symbol": "603501", "name": "韦尔股份", "industry": "半导体"},
    {"ts_code": "603659.SH", "symbol": "603659", "name": "璞泰来", "industry": "锂电池"},
    {"ts_code": "603799.SH", "symbol": "603799", "name": "华友钴业", "industry": "有色"},
    {"ts_code": "603986.SH", "symbol": "603986", "name": "兆易创新", "industry": "半导体"},
]


def search_stock_local(keyword: str) -> list:
    """
    在本地股票列表中搜索

    Parameters
    ----------
    keyword : str
        搜索关键词

    Returns
    -------
    list
        匹配的股票列表
    """
    keyword = keyword.strip().lower()
    if not keyword:
        return []

    results = []
    for stock in STOCK_LIST:
        if (keyword in stock['ts_code'].lower() or
            keyword in stock['symbol'].lower() or
            keyword in stock['name'].lower() or
            keyword in stock['industry'].lower()):
            results.append(stock)

    return results


if __name__ == "__main__":
    # 测试
    print("测试搜索 '平安':")
    results = search_stock_local("平安")
    for r in results[:5]:
        print(f"  {r['ts_code']} - {r['name']} ({r['industry']})")

    print("\n测试搜索 '600519':")
    results = search_stock_local("600519")
    for r in results[:5]:
        print(f"  {r['ts_code']} - {r['name']} ({r['industry']})")
