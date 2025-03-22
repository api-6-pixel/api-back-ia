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
    
class ProjecaoCrescimento(BaseModel):
    meses_projecao: int
    teto_gastos: int

class ConsultaMensal(BaseModel):
    mes: int
    
class DadosAtualizacao(BaseModel):
    umidadeSolo: float
    temperaturaAmbiente: float
    temperaturaSolo: float
    umidadeAmbiente: float
    indiceUV: float
    phSolo: float
    
def mapear_para_entrada_diaria(atualizacao: DadosAtualizacao) -> EntradaDiaria:
    return EntradaDiaria(
        Soil_Moisture=atualizacao.umidadeSolo,
        Ambient_Temperature=atualizacao.temperaturaAmbiente,
        Soil_Temperature=atualizacao.temperaturaSolo,
        Humidity=atualizacao.umidadeAmbiente,
        Light_Intensity=atualizacao.indiceUV,
        Soil_pH=atualizacao.phSolo
    )


@app.post("/incluir-atualizacao")
def status_mensal(atualizacao: DadosAtualizacao):
    try:
        entrada_diaria = mapear_para_entrada_diaria(atualizacao)
        status_hoje = plant_service.prever_status(entrada_diaria)
        plant_service.salvar_status(status_hoje)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/projetar_crescimento/v1")
def projetar_crescimento(dados: ProjecaoCrescimento):
    try:
        ultimos_status = plant_service.carregar_ultimos_status(n=1)
        if not ultimos_status:
            raise HTTPException(status_code=404, detail="Nenhum status encontrado no banco de dados.")

        status_hoje = ultimos_status[0]
        crescimento_hoje = plant_service.crescimento_medio.get(status_hoje, "Desconhecido")

        ultimos_status = plant_service.carregar_ultimos_status(n=7)
        if not ultimos_status:
            crescimento_futuro = ["Indefinido"] * dados.meses_projecao
        else:
            tendencia = plant_service.calcular_tendencia(ultimos_status)
            crescimento_futuro = plant_service.projetar_crescimento_mensal(tendencia, dados.meses_projecao)

        meses_nomes = [calendar.month_name[(datetime.utcnow().month + i) % 12 or 12] for i in range(dados.meses_projecao)]

        gastos_projetados = []
        total_gastos_acumulados = 0

        for status in crescimento_futuro:
            if status == "Alto":
                gasto_mensal = 5
            elif status == "Médio":
                gasto_mensal = 10
            else:
                gasto_mensal = 15

            total_gastos_acumulados += gasto_mensal 
            gastos_projetados.append(total_gastos_acumulados)

        return {
            "status_atual": crescimento_hoje,
            "meses": meses_nomes,
            "crescimento": crescimento_futuro,
            "gastos_projetados": gastos_projetados, 
            "teto_gastos": dados.teto_gastos 
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