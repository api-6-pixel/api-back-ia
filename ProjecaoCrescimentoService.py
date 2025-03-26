import pickle
from pymongo import MongoClient
from datetime import datetime
from collections import Counter
import numpy as np
import random

class ProjecaoCrescimentoService:
    def __init__(self):
        with open('modelo_classificacao_rn.pkl', 'rb') as f:
            self.modelo = pickle.load(f)
        with open('scaler_plant.pkl', 'rb') as f:
            self.scaler = pickle.load(f)

        self.crescimento_medio = {
            'Healthy': 'Alto',
            'Moderate Stress': 'Médio',
            'High Stress': 'Baixo'
        }

        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client.plantas_db
        self.historico_collection = self.db.historico

    def salvar_status(self, status, entrada_diaria):
        self.historico_collection.insert_one({
            "status": status,
            "data": datetime.utcnow(),
	    "fazendaNome": entrada_diaria.Fazenda_Nome
        })

    def carregar_ultimos_status(self,fazenda:str, n=7):
        pipeline = [
            {"$match": { "fazendaNome": fazenda }},
            {"$sort": {"data": -1}},
            {"$limit": n},
            {"$project": {"status": 1}}
        ]
        resultados = list(self.historico_collection.aggregate(pipeline))
        return [resultado['status'] for resultado in resultados]

    def buscar_status_mensal(self, mes: int, fazendaNome):
        ano = datetime.now().year

        data_inicio = datetime(ano, mes, 1)
        if mes == 12:
            data_fim = datetime(ano + 1, 1, 1)
        else:
            data_fim = datetime(ano, mes + 1, 1)

        registros = self.historico_collection.find({
            "data": {
                "$gte": data_inicio,
                "$lt": data_fim
            }
        })

        resultado = []
        for registro in registros:
            dia = registro["data"].day
            status = self.crescimento_medio.get(registro["status"], "Desconhecido")
            resultado.append({"dia": dia, "status": status})

        resultado.sort(key=lambda x: x["dia"])

        return resultado

    def prever_status(self, dados):
        entrada = np.array([
            [dados.Soil_Moisture, dados.Ambient_Temperature, dados.Soil_Temperature,
             dados.Humidity, dados.Light_Intensity, dados.Soil_pH]
        ])
        entrada = self.scaler.transform(entrada)

        status_hoje = self.modelo.predict(entrada)[0]
        return status_hoje

    def calcular_tendencia(self, ultimos_status):
        status_count = Counter(ultimos_status)
        mais_comum = status_count.most_common(1)[0][0]
        return self.crescimento_medio.get(mais_comum, "Desconhecido")

    def projetar_crescimento_mensal(self, tendencia, meses_projecao):
        crescimento_mensal = []
        for mes in range(1, meses_projecao + 1):
            if tendencia == "Alto":
                # Se a tendência é "Alto", há uma chance pequena de piorar
                crescimento_mensal.append(random.choices(["Alto", "Médio"], weights=[0.8, 0.2])[0])
            elif tendencia == "Médio":
                # Se a tendência é "Médio", pode melhorar ou piorar
                crescimento_mensal.append(random.choices(["Alto", "Médio", "Baixo"], weights=[0.3, 0.5, 0.2])[0])
            else:
                # Se a tendência é "Baixo", há uma chance pequena de melhorar
                crescimento_mensal.append(random.choices(["Médio", "Baixo"], weights=[0.2, 0.8])[0])
        return crescimento_mensal
