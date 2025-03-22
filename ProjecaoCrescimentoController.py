from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict
import calendar

from ProjecaoCrescimentoService import ProjecaoCrescimentoService

plant_service = ProjecaoCrescimentoService()
app = FastAPI()

class EntradaDiaria(BaseModel):
    Soil_Moisture: float
    Ambient_Temperature: float
    Soil_Temperature: float
    Humidity: float
    Light_Intensity: float
    Soil_pH: float
    meses_projecao: int

class ConsultaMensal(BaseModel):
    mes: int

@app.post("/projetar_crescimento/v1")
def projetar_crescimento(dados: EntradaDiaria):
    try:
        status_hoje = plant_service.prever_status(dados)
        plant_service.salvar_status(status_hoje)

        crescimento_hoje = plant_service.crescimento_medio.get(status_hoje, "Desconhecido")

        ultimos_status = plant_service.carregar_ultimos_status(n=7)
        if not ultimos_status:
            crescimento_futuro = ["Indefinido"] * dados.meses_projecao
        else:
            tendencia = plant_service.calcular_tendencia(ultimos_status)
            crescimento_futuro = plant_service.projetar_crescimento_mensal(tendencia, dados.meses_projecao)

        meses_nomes = [calendar.month_name[(datetime.utcnow().month + i) % 12 or 12] for i in range(dados.meses_projecao)]

        return {
            "status_atual": crescimento_hoje,
            "meses": meses_nomes,
            "crescimento": crescimento_futuro
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/status_mensal/v1")
def status_mensal(consulta: ConsultaMensal):
    try:
        if consulta.mes < 1 or consulta.mes > 12:
            raise HTTPException(status_code=400, detail="Mês inválido. Deve ser um valor entre 1 e 12.")

        status_mensal = plant_service.buscar_status_mensal(consulta.mes)

        return status_mensal
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))