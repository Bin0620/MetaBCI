#include "sys.h"
#include "usart.h"
#include "delay.h"
		  
//����2�����Բ�����ͨѶ
//����2ֻ�н���
u8 receive[36]={0};	//�Բ��������	
u8 receive_ok = 0;  //������ɱ�־

u8 attention = 0;    //ע����
u8 meditation = 0;   //���ɶ�
//�ź�����
//u8 signalquality = 0;
//У���
u16  Checksum = 0;

//��ʼ��IO ����1 
//bound:������
void uart_init(u32 bound2)
{
	
	//GPIO�˿�����
    GPIO_InitTypeDef GPIO_InitStructure;
	USART_InitTypeDef USART_InitStructure;
	NVIC_InitTypeDef NVIC_InitStructure;
	
	//����2ʱ�� 
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE);	//ʹ��USART2��GPIOAʱ��
	RCC_APB1PeriphClockCmd(RCC_APB1Periph_USART2, ENABLE);
	
    USART_DeInit(USART2);  //��λ����2	    
		
	//����2�������
	//USART2_TX   PA.2		--> RX
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_2; //PA.2
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF_PP;	//�����������
    GPIO_Init(GPIOA, &GPIO_InitStructure); //��ʼ��PA2
   
    //USART2_RX	  PA.3	   -->TX
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_3;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IN_FLOATING;//��������
    GPIO_Init(GPIOA, &GPIO_InitStructure);  //��ʼ��PA3
		
	//Usart2 NVIC ����
    NVIC_InitStructure.NVIC_IRQChannel = USART2_IRQn;
	NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority=3 ;//��ռ���ȼ�3
	NVIC_InitStructure.NVIC_IRQChannelSubPriority = 3;		//�����ȼ�3
	NVIC_InitStructure.NVIC_IRQChannelCmd = ENABLE;			//IRQͨ��ʹ��
	NVIC_Init(&NVIC_InitStructure);	//����ָ���Ĳ�����ʼ��VIC�Ĵ���
		
	//USART2 ��ʼ������
	USART_InitStructure.USART_BaudRate = bound2;//һ������Ϊ9600;
	USART_InitStructure.USART_WordLength = USART_WordLength_8b;//�ֳ�Ϊ8λ���ݸ�ʽ
	USART_InitStructure.USART_StopBits = USART_StopBits_1;//һ��ֹͣλ
	USART_InitStructure.USART_Parity = USART_Parity_No;//����żУ��λ
	USART_InitStructure.USART_HardwareFlowControl = USART_HardwareFlowControl_None;//��Ӳ������������
    USART_InitStructure.USART_Mode = USART_Mode_Rx;//����ģʽ

    USART_Init(USART2, &USART_InitStructure);//��ʼ������2
	USART_ITConfig(USART2, USART_IT_RXNE,ENABLE);//���������ж�
    USART_Cmd(USART2, ENABLE);                //ʹ�ܴ��� 2
}


//�Բ����ݽ��մ���
u8 receive_del(void)
{
	u8 i = 0;	
	if(receive_ok)
	{
		receive_ok = 0;
		for(i = 0; i < 32; i++)
		{  
			Checksum += receive[i+3];
		}      
		Checksum = (~Checksum)&0xff; 
		if(Checksum == receive[35])
		{      
			Checksum = 0; 
			//signalquality = 0;
			attention = 0;    
			meditation = 0;  
			
			//signalquality = receive[4];     
			attention = receive[32];
			meditation = receive[34];
		}
	}
	return attention;
}


/***********************************************************************************************************************/
//����2�жϷ�������������������¼���ֻ���մ���
//�Բ������������մ���
void USART2_IRQHandler(void)                	
{
	
	u16 data=0;	
	static u8 count;
	//���մ���
	if(USART_GetITStatus(USART2, USART_IT_RXNE) != RESET)
	{
		data = USART_ReceiveData(USART2);//��ȡ���յ�������
		receive[count] = (u8)(data&0x00ff);//ȡ��8λ����
		
		if(count==0&&receive[count]==0xAA)
    {  
      count++;  
    } 
    else if(count==1&&receive[count]==0xAA)
    {  
      count++;  
    }
    else if(count==2&&receive[count]==0x20)
    {  
      count++;  
    }    
    else if(count==3&&receive[count]==0x02)
    {  
      count++;  
    }  
    else if(count==4)
    {  
      count++;
    }
    else if(count==5&&receive[count]==0x83)
    {  
      count++;
    }
    else if(count==6&&receive[count]==0x18)
    {  
      count++;
    }
    else if (count >=7 && count < 35)
    {
      count++; 
    }        
    else if(count==35)
    {  
      count=0;    
      receive_ok = 1;
    }  
    else
    {  
      count=0;
    }
	}
} 




