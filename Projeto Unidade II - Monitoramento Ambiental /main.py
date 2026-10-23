# UNIVERSIDADE FEDERAL DO RIO GRANDE DO NORTE
# DEPARTAMENTO DE ENGENHARIA DE COMPUTACAO E AUTOMACAO
# REDES DE COMPUTADORES (DCA3605)
# CLIENTE TCP - SISTEMA DE MONITORAMENTO AMBIENTAL

from socket import *
import sys

# Definicao de IP e Porta padrao do servidor
serverName = '10.13.123.0'
serverPort = 54321

# Permite informar outro IP pela linha de comando (Somente usado para testes)
if len(sys.argv) > 1:
    serverName = sys.argv[1]


# Funcao para exibir as medicoes de uma estacao
def exibir_medicoes(dados_ciclo):
    estacao = dados_ciclo.get('estacao', '---')
    local = dados_ciclo.get('local', 'DESCONHECIDO')
    ciclo = dados_ciclo.get('ciclo', '---')

    temp = dados_ciclo.get('temp', 'N/A')
    temp_unit = dados_ciclo.get('temp_unit', 'C')

    hum = dados_ciclo.get('hum', 'N/A')
    hum_unit = dados_ciclo.get('hum_unit', '%')

    press = dados_ciclo.get('press', 'N/A')
    press_unit = dados_ciclo.get('press_unit', 'hPa')

    print("-----------------------------------")
    print(f" ESTACAO {estacao} - {local}")
    print("-----------------------------------")
    print(f" Ciclo       : {ciclo}")
    print(f" Temperatura : {temp} {temp_unit}")
    print(f" Umidade     : {hum} {hum_unit}")
    print(f" Pressao     : {press} {press_unit}")
    print("-----------------------------------")
    print(" Aguardando novas medicoes...\n")


# Criacao do socket TCP
clientSocket = socket(AF_INET, SOCK_STREAM)

try:
    print("==========================================")
    print("  SISTEMA DE MONITORAMENTO AMBIENTAL")
    print("==========================================")
    print(f"Conectando ao servidor TCP em {serverName}:{serverPort}...")

    # Estabelecimento da conexao com o servidor
    clientSocket.connect((serverName, serverPort))
    print("Conexao estabelecida com sucesso!\n")

    # Recebe a mensagem inicial do servidor
    clientSocket.settimeout(2.0)

    try:
        msg_inicial = clientSocket.recv(1024).decode(
            'utf-8', errors='replace'
        )

        if msg_inicial:
            print(f"Servidor: {msg_inicial.strip()}")

    except timeout:
        print("Nenhuma mensagem inicial recebida.")

    clientSocket.settimeout(None)

    # Solicita a lista de estacoes disponiveis
    print("\nEnviando comando LIST...")
    clientSocket.sendall("LIST\r\n".encode('utf-8'))

    resp_list = clientSocket.recv(1024).decode(
        'utf-8', errors='replace'
    ).strip()

    partes_list = resp_list.split(';')

    if len(partes_list) > 2 and partes_list[0] == '210':
        estacoes = partes_list[2:]
        print("Estacoes disponiveis:", ", ".join(estacoes))
    else:
        print(f"Resposta inesperada do servidor: {resp_list}")
        sys.exit(1)

    # Escolha da estacao pelo usuario
    estacao_escolhida = input("\nSelecione uma estacao: ").strip()

    # Verifica se a estacao escolhida esta disponivel
    if estacao_escolhida not in estacoes:
        print("Estacao invalida. Encerrando conexao.")
        sys.exit(1)

    # Solicita o envio continuo de medicoes da estacao escolhida
    comando_stream = f"STREAM;{estacao_escolhida}\r\n"

    print(f"\nEnviando comando para a estacao {estacao_escolhida}...")
    clientSocket.sendall(comando_stream.encode('utf-8'))

    print("\nIniciando monitoramento continuo...\n")

    # Buffer para armazenar dados recebidos pela rede
    buffer = ""

    # Dicionario com as medicoes do ciclo atual
    dados_ciclo_atual = {}

    # Indica se um ciclo de medicoes esta sendo recebido
    em_ciclo = False

    while True:
        # Recebe dados do servidor
        dados_bytes = clientSocket.recv(1024)

        # Verifica se o servidor encerrou a conexao
        if not dados_bytes:
            print("Conexao encerrada pelo servidor.")
            break

        # Adiciona os dados recebidos ao buffer
        buffer += dados_bytes.decode('utf-8', errors='replace')

        # Processa todas as linhas completas recebidas
        while "\n" in buffer:
            linha, buffer = buffer.split("\n", 1)
            linha = linha.strip()

            if not linha:
                continue

            campos = linha.split(';')
            tipo_registro = campos[0]

            # Confirmacao de inicio do fluxo de medicoes
            if tipo_registro == '220':
                if len(campos) >= 3 and campos[1] == 'STREAM_STARTED':
                    print(
                        f"Monitoramento iniciado para a estacao {campos[2]}.\n"
                    )

            # Inicio de um ciclo de medicoes
            elif tipo_registro == 'BEGIN' and len(campos) >= 3:
                em_ciclo = True

                dados_ciclo_atual = {
                    'estacao': campos[1],
                    'ciclo': campos[2]
                }

            # Informacoes da estacao
            elif tipo_registro == 'INFO' and em_ciclo and len(campos) >= 3:
                dados_ciclo_atual['local'] = campos[2]

            # Temperatura
            elif tipo_registro == 'TEMP' and em_ciclo and len(campos) >= 3:
                dados_ciclo_atual['temp'] = campos[1]
                dados_ciclo_atual['temp_unit'] = campos[2]

            # Umidade
            elif tipo_registro == 'HUM' and em_ciclo and len(campos) >= 3:
                dados_ciclo_atual['hum'] = campos[1]

                if campos[2] == 'PCT':
                    dados_ciclo_atual['hum_unit'] = '%'
                else:
                    dados_ciclo_atual['hum_unit'] = campos[2]

            # Pressao atmosferica
            elif tipo_registro == 'PRESS' and em_ciclo and len(campos) >= 3:
                dados_ciclo_atual['press'] = campos[1]

                if campos[2] == 'HPA':
                    dados_ciclo_atual['press_unit'] = 'hPa'
                else:
                    dados_ciclo_atual['press_unit'] = campos[2]

            # Final de um ciclo de medicoes
            elif tipo_registro == 'END' and em_ciclo:
                exibir_medicoes(dados_ciclo_atual)

                dados_ciclo_atual = {}
                em_ciclo = False

            # Respostas de erro do servidor
            elif tipo_registro == '400':
                print(f"Erro informado pelo servidor: {linha}")

except KeyboardInterrupt:
    print("\nMonitoramento encerrado pelo usuario (Ctrl+C).")

except ConnectionRefusedError:
    print(
        f"\nNao foi possivel conectar ao servidor "
        f"em {serverName}:{serverPort}."
    )

except timeout:
    print("\nTempo limite de recepcao excedido.")

except Exception as e:
    print(f"\nErro de conexao/comunicacao: {e}")

finally:
    clientSocket.close()
    print("Socket do cliente fechado.")
