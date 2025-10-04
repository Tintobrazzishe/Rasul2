#!/usr/bin/env python3
"""
NFT Liquidity Position Report для Base Network
Отчет по NFT позициям в пулах ликвидности (Aerodrome, Uniswap V3) на Base
"""

import requests
import json
from typing import List, Dict
from datetime import datetime

# API Configuration
ETHERSCAN_API_KEY = "YX7MA3VZR4IB3YAF3VV9CZ2E2W1WVP6JSG"
WALLET_ADDRESS = "0xb3563C2F6B34a559C8cD8042F8AEfe1EbACd620E"

# BaseScan API endpoints (Etherscan for Base network)
BASE_API_URL = "https://api.basescan.org/api"

# Known NFT contracts for liquidity positions on Base
UNISWAP_V3_POSITIONS_BASE = "0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1"
AERODROME_POSITIONS = "0x827922686190790b37229fd06084350E74485b72"

def get_nft_tokens(wallet: str, api_key: str) -> List[Dict]:
    """
    Получить все ERC721 токены (NFTs) для указанного кошелька через BaseScan API v2
    """
    params = {
        "module": "account",
        "action": "tokennfttx",
        "address": wallet,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "asc",
        "apikey": api_key
    }
    
    try:
        response = requests.get(BASE_API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data["status"] == "1":
            return data["result"]
        else:
            print(f"⚠️ API вернул статус: {data.get('message', 'Unknown error')}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка при запросе к API: {e}")
        return []

def get_erc721_balance(wallet: str, contract: str, api_key: str) -> int:
    """
    Получить баланс ERC721 токенов для конкретного контракта
    """
    params = {
        "module": "stats",
        "action": "tokensupply",
        "contractaddress": contract,
        "apikey": api_key
    }
    
    try:
        response = requests.get(BASE_API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return int(data.get("result", 0)) if data["status"] == "1" else 0
    except Exception as e:
        print(f"⚠️ Не удалось получить баланс для {contract}: {e}")
        return 0

def filter_liquidity_positions(transactions: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Фильтровать транзакции и группировать позиции по протоколам
    """
    positions = {
        "Uniswap V3": [],
        "Aerodrome": [],
        "Other": []
    }
    
    # Отслеживаем текущие позиции (mint - burn)
    current_tokens = {}
    
    for tx in transactions:
        contract = tx.get("contractAddress", "").lower()
        token_id = tx.get("tokenID", "")
        from_addr = tx.get("from", "").lower()
        to_addr = tx.get("to", "").lower()
        
        # Проверяем, является ли это получением или отправкой NFT
        is_received = to_addr == WALLET_ADDRESS.lower()
        is_sent = from_addr == WALLET_ADDRESS.lower()
        
        if is_received:
            # Получили NFT
            tx_info = {
                "tokenID": token_id,
                "hash": tx.get("hash", ""),
                "timeStamp": tx.get("timeStamp", ""),
                "blockNumber": tx.get("blockNumber", ""),
                "from": from_addr,
                "status": "ACTIVE"
            }
            
            if contract == UNISWAP_V3_POSITIONS_BASE.lower():
                current_tokens[f"uni-{token_id}"] = tx_info
                positions["Uniswap V3"].append(tx_info)
            elif contract == AERODROME_POSITIONS.lower():
                current_tokens[f"aero-{token_id}"] = tx_info
                positions["Aerodrome"].append(tx_info)
            else:
                current_tokens[f"other-{contract}-{token_id}"] = tx_info
                positions["Other"].append(tx_info)
        
        elif is_sent:
            # Отправили NFT (закрыли позицию)
            for key in list(current_tokens.keys()):
                if token_id in key:
                    if key in current_tokens:
                        current_tokens[key]["status"] = "CLOSED"
                        del current_tokens[key]
    
    # Возвращаем только активные позиции
    active_positions = {
        "Uniswap V3": [p for p in positions["Uniswap V3"] if p.get("status") == "ACTIVE"],
        "Aerodrome": [p for p in positions["Aerodrome"] if p.get("status") == "ACTIVE"],
        "Other": [p for p in positions["Other"] if p.get("status") == "ACTIVE"]
    }
    
    return active_positions

def format_timestamp(timestamp: str) -> str:
    """
    Форматировать timestamp в читаемый вид
    """
    try:
        dt = datetime.fromtimestamp(int(timestamp))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp

def generate_report(positions: Dict[str, List[Dict]], wallet: str) -> str:
    """
    Генерировать отчет по позициям
    """
    report = []
    report.append("=" * 80)
    report.append("📊 ОТЧЕТ ПО NFT ПОЗИЦИЯМ В ПУЛАХ ЛИКВИДНОСТИ")
    report.append("=" * 80)
    report.append(f"\n🔹 Кошелек: {wallet}")
    report.append(f"🔹 Сеть: Base")
    report.append(f"🔹 Дата отчета: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("\n" + "=" * 80 + "\n")
    
    total_positions = sum(len(v) for v in positions.values())
    report.append(f"📈 Всего активных позиций: {total_positions}\n")
    
    for protocol, txs in positions.items():
        if not txs:
            continue
            
        report.append(f"\n{'=' * 80}")
        report.append(f"🏦 {protocol.upper()}")
        report.append(f"{'=' * 80}")
        report.append(f"Количество позиций: {len(txs)}\n")
        
        for idx, tx in enumerate(txs, 1):
            report.append(f"  [{idx}] Token ID: {tx['tokenID']}")
            report.append(f"      📅 Дата получения: {format_timestamp(tx['timeStamp'])}")
            report.append(f"      🧱 Block: {tx['blockNumber']}")
            report.append(f"      📝 TX Hash: {tx['hash']}")
            report.append(f"      🔄 Статус: {tx['status']}")
            report.append("")
    
    if total_positions == 0:
        report.append("\n⚠️ Активных позиций не найдено.")
        report.append("   Возможные причины:")
        report.append("   - Кошелек не имеет NFT позиций в ликвидности")
        report.append("   - Все позиции были закрыты")
        report.append("   - Используется другой адрес контракта для LP NFT")
    
    report.append("\n" + "=" * 80)
    report.append("📋 ИНФОРМАЦИЯ О КОНТРАКТАХ")
    report.append("=" * 80)
    report.append(f"Uniswap V3 Positions: {UNISWAP_V3_POSITIONS_BASE}")
    report.append(f"Aerodrome Positions: {AERODROME_POSITIONS}")
    report.append("\n" + "=" * 80 + "\n")
    
    return "\n".join(report)

def main():
    """
    Основная функция для генерации отчета
    """
    print("🚀 Запуск сбора данных по NFT ликвидным позициям...\n")
    print(f"📍 Кошелек: {WALLET_ADDRESS}")
    print(f"🌐 Сеть: Base (BaseScan API)")
    print(f"🔑 API Key: {ETHERSCAN_API_KEY[:8]}...\n")
    
    # Получаем все NFT транзакции
    print("📥 Загрузка ERC721 транзакций...")
    nft_transactions = get_nft_tokens(WALLET_ADDRESS, ETHERSCAN_API_KEY)
    print(f"✅ Получено {len(nft_transactions)} транзакций\n")
    
    if nft_transactions:
        # Фильтруем и группируем позиции
        print("🔍 Анализ позиций в пулах ликвидности...")
        positions = filter_liquidity_positions(nft_transactions)
        
        # Генерируем отчет
        report = generate_report(positions, WALLET_ADDRESS)
        print(report)
        
        # Сохраняем отчет в файл
        filename = f"nft_liquidity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n💾 Отчет сохранен в файл: {filename}")
    else:
        print("❌ Не удалось получить данные о NFT транзакциях")
        print("   Проверьте:")
        print("   - Правильность API ключа")
        print("   - Доступность BaseScan API")
        print("   - Наличие NFT в указанном кошельке")

if __name__ == "__main__":
    main()
