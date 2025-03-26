from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict
from typing import Optional
import logging


from ProjecaoCrescimentoService import ProjecaoCrescimentoService

plant_service = ProjecaoCrescimentoService()
app = FastAPI()

# Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

class EntradaDiaria(BaseModel):
    Soil_Moisture: float
    Ambient_Temperature: float
    Soil_Temperature: float
    Humidity: float
    Light_Intensity: float
    Soil_pH: float
    
class ProjecaoCrescimento(BaseModel):
    meses_projecao: int
    fazenda_nome: str

class ConsultaMensal(BaseModel):
    mes: int

class DadosAtualizacao(BaseModel):
    fazendaNome: str
    umidadeSolo: float
    temperaturaAmbiente: float
    temperaturaSolo: float
    umidadeAmbiente: float
    indiceUV: float
    phSolo: float
    custoEsperado: Optional[float] = None
    
def mapear_para_entrada_diaria(atualizacao: DadosAtualizacao) -> EntradaDiaria:
    return EntradaDiaria(
        Soil_Moisture=atualizacao.umidadeSolo,
        Ambient_Temperature=atualizacao.temperaturaAmbiente,
        Soil_Temperature=atualizacao.temperaturaSolo,
        Humidity=atualizacao.umidadeAmbiente,
        Light_Intensity=atualizacao.indiceUV,
        Soil_pH=atualizacao.phSolo
    )

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.post("/incluir-atualizacao")
def incluir_atualizacao(atualizacao: DadosAtualizacao):
    try:
        entrada_diaria = mapear_para_entrada_diaria(atualizacao)
        status_hoje = plant_service.prever_status(entrada_diaria)
        plant_service.salvar_status(status_hoje, atualizacao.fazendaNome)
        plant_service.salvar_custo(atualizacao.custoEsperado, atualizacao.fazendaNome)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/projetar_crescimento/v1")
def projetar_crescimento(dados: ProjecaoCrescimento):
    try:
        ultimos_status = plant_service.carregar_ultimos_status(dados.fazenda_nome,n=1)
        if not ultimos_status:
            return JSONResponse(status_code=400,
                 content={"detail": f"Nenhuma fazenda encontrada para: {dados.fazenda_nome}."})
            
        status_hoje = ultimos_status[0]
        crescimento_hoje = plant_service.crescimento_medio.get(status_hoje, "Desconhecido")
        
        ultimos_status = plant_service.carregar_ultimos_status(dados.fazenda_nome, n=7)
        if not ultimos_status:
            crescimento_futuro = ["Indefinido"] * dados.meses_projecao
        else:
            tendencia = plant_service.calcular_tendencia(ultimos_status)
            crescimento_futuro = plant_service.projetar_crescimento_mensal(tendencia, dados.meses_projecao)
           
        meses_nomes = [f"Mês {i+1}" for i in range(dados.meses_projecao)]
        
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
            teto_gastos = plant_service.get_custo_fazenda(dados.fazenda_nome)["custo"]
            
        return {
            "status_atual": crescimento_hoje,
            "meses": meses_nomes,
            "crescimento": crescimento_futuro,
            "gastos_projetados": gastos_projetados,
            "teto_gastos": teto_gastos
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/status_mensal/v1")
def status_mensal(consulta: ConsultaMensal):
    try:
        status_mensal = plant_service.buscar_status_mensal(consulta.mes)
        return status_mensal
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
