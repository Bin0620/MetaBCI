#include "sys.h"
#include "usart.h"
#include "delay.h"
		  
//串口2负责脑波蓝牙通讯
//串口2只有接收
u8 receive[36]={0};	//脑波大包数据	
u8 receive_ok = 0;  //接收完成标志

u8 attention = 0;    //注意力
u8 meditation = 0;   //放松度
//信号质量
//u8 signalquality = 0;
//校验和
u16  Checksum = 0;

//初始化IO 串口1 
//bound:波特率
void uart_init(u32 bound2)
{
	
	//GPIO端口设置
    GPIO_InitTypeDef GPIO_InitStructure;
	USART_InitTypeDef USART_InitStructure;
	NVIC_InitTypeDef NVIC_InitStructure;
	
	//串口2时钟 
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE);	//使能USART2，GPIOA时钟
	RCC_APB1PeriphClockCmd(RCC_APB1Periph_USART2, ENABLE);
	
    USART_DeInit(USART2);  //复位串口2	    
		
	//串口2相关配置
	//USART2_TX   PA.2		--> RX
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_2; //PA.2
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF_PP;	//复用推挽输出
    GPIO_Init(GPIOA, &GPIO_InitStructure); //初始化PA2
   
    //USART2_RX	  PA.3	   -->TX
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_3;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IN_FLOATING;//浮空输入
    GPIO_Init(GPIOA, &GPIO_InitStructure);  //初始化PA3
		
	//Usart2 NVIC 配置
    NVIC_InitStructure.NVIC_IRQChannel = USART2_IRQn;
	NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority=3 ;//抢占优先级3
	NVIC_InitStructure.NVIC_IRQChannelSubPriority = 3;		//子优先级3
	NVIC_InitStructure.NVIC_IRQChannelCmd = ENABLE;			//IRQ通道使能
	NVIC_Init(&NVIC_InitStructure);	//根据指定的参数初始化VIC寄存器
		
	//USART2 初始化设置
	USART_InitStructure.USART_BaudRate = bound2;//一般设置为9600;
	USART_InitStructure.USART_WordLength = USART_WordLength_8b;//字长为8位数据格式
	USART_InitStructure.USART_StopBits = USART_StopBits_1;//一个停止位
	USART_InitStructure.USART_Parity = USART_Parity_No;//无奇偶校验位
	USART_InitStructure.USART_HardwareFlowControl = USART_HardwareFlowControl_None;//无硬件数据流控制
    USART_InitStructure.USART_Mode = USART_Mode_Rx;//接收模式

    USART_Init(USART2, &USART_InitStructure);//初始化串口2
	USART_ITConfig(USART2, USART_IT_RXNE,ENABLE);//开启接收中断
    USART_Cmd(USART2, ENABLE);                //使能串口 2
}


//脑波数据接收处理
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
//串口2中断服务程序，用来处理蓝牙事件，只接收处理
//脑波数据蓝牙接收处理
void USART2_IRQHandler(void)                	
{
	
	u16 data=0;	
	static u8 count;
	//接收处理
	if(USART_GetITStatus(USART2, USART_IT_RXNE) != RESET)
	{
		data = USART_ReceiveData(USART2);//读取接收到的数据
		receive[count] = (u8)(data&0x00ff);//取低8位数据
		
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




