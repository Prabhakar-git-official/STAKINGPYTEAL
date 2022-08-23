from pyteal import *

def approval_program():
    on_creation = Seq(
        [
            App.globalPut(Bytes("Creator"), Txn.sender()),
            App.globalPut(Bytes("Totalstaked"), Int(0)),
            App.globalPut(Bytes("GlobalShare"), Int(0)),
            App.globalPut(Bytes("GlobalTime"), Int(0)),
            App.globalPut(Bytes("RewardPool"), Btoi(Txn.application_args[0])),
            Return(Int(1))
        ]
    )

    is_creator = Txn.sender() == App.globalGet(Bytes("Creator"))

    totalstaked_amount = App.globalGet(Bytes("Totalstaked"))

    amount = Gtxn[1].asset_amount()  

    unstakeamount=Btoi(Txn.application_args[1])

    get_stakedamount_of_sender = App.localGetEx(Int(0), App.id(), Bytes("MyStakedAmount"))

    get_UserShare = App.localGetEx(Int(0), App.id(), Bytes("UserShare"))
     
    get_GlobalShare = App.globalGet(Bytes("GlobalShare"))
     
    get_UserTime = App.localGetEx(Int(0), App.id(), Bytes("UserTime"))
    
    get_CurrentTime = Global.latest_timestamp()

    get_GlobalTime = App.globalGet(Bytes("GlobalTime"))

    get_stakeasset =App.globalGet(Bytes("SA"))

    get_Rewardasset =App.globalGet(Bytes("RA"))
  
    get_RewardPool = App.globalGet(Bytes("RewardPool"))
    
    
    on_closeout = Seq(
        [
            Return(Int(1))
        ]
    )

    appopt_in = Return(
       Int(1)
    )
  
    check_creator = Return(
        is_creator
    )

    Optin = Seq(
            # Assert(Global.group_size()==Int(1)),
            Assert(Txn.sender() == App.globalGet(Bytes("Creator"))),
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum : TxnType.AssetTransfer,
                TxnField.xfer_asset: Btoi(Txn.application_args[1]),
                TxnField.asset_amount : Int(0),
                TxnField.asset_receiver : Global.current_application_address(),
            }),
        InnerTxnBuilder.Submit(),
            Return(Int(1))
    )  

    update = Seq(
        [
            Assert(Txn.sender() == App.globalGet(Bytes("Creator"))),
            Assert(Txn.application_args.length() == Int(2)),
            App.globalPut(Bytes("SA"), Btoi(Txn.application_args[0])),
            App.globalPut(Bytes("RA"), Btoi(Txn.application_args[1])),
            Return(Int(1))
        ]
    )

    @Subroutine(TealType.uint64)
    def GlobalStakeShare():
        return ((((get_CurrentTime - get_GlobalTime))*totalstaked_amount)/ Int(86400))
    
   
    UserStakeShare = Seq(
            [
            get_UserTime,
            get_stakedamount_of_sender,
            App.localPut(Int(0), Bytes("UserShare"),(((get_CurrentTime - get_UserTime.value()))*get_stakedamount_of_sender.value())/Int(86400)),
            ]
    )
    Stake = Seq(
        [
            Assert(Global.group_size()==Int(2)),
            Assert(Gtxn[1].type_enum()==TxnType.AssetTransfer),
            Assert(Gtxn[1].asset_receiver() == Global.current_application_address()),
            Assert(Gtxn[1].xfer_asset() == get_stakeasset),
            Assert(amount>=Int(1)),
            App.globalPut(Bytes("Totalstaked"), totalstaked_amount + amount), 
            get_stakedamount_of_sender,
            If(get_stakedamount_of_sender.hasValue())
            .Then(App.localPut(Int(0), Bytes("MyStakedAmount"), get_stakedamount_of_sender.value() + Gtxn[1].asset_amount()))
            .Else(App.localPut(Int(0), Bytes("MyStakedAmount"), Gtxn[1].asset_amount())),
            UserStakeShare,
            App.globalPut(Bytes("GlobalShare"),GlobalStakeShare()),
            App.localPut(Int(0), Bytes("UserTime"),Global.latest_timestamp()),
            App.globalPut(Bytes("GlobalTime"),Global.latest_timestamp()),
            Return(Int(1))
        ]
    )

    @Subroutine(TealType.none)
    def Transfer(assetID,Amount):
        return Seq(
            [
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum : TxnType.AssetTransfer,
                TxnField.xfer_asset: assetID,
                TxnField.asset_amount : Amount,
                TxnField.asset_receiver : Txn.sender(),
            }),
            InnerTxnBuilder.Submit(),
            ]
        )
   
    Unstake = Seq(
        [
            # Assert(Global.group_size()==Int(2)),
            # Assert(Gtxn[1].type_enum()==TxnType.AssetTransfer), 
            # Assert(Gtxn[1].asset_receiver() == Txn.sender()),
            # Assert(Gtxn[1].sender() == Global.current_application_address()),
            App.globalPut(Bytes("Totalstaked"), totalstaked_amount - unstakeamount), 
            get_stakedamount_of_sender,
            Assert(unstakeamount <= get_stakedamount_of_sender.value()),
            Assert(get_stakedamount_of_sender.hasValue()),
            App.localPut(Int(0), Bytes("MyStakedAmount"), get_stakedamount_of_sender.value() - unstakeamount),
            UserStakeShare,
            App.globalPut(Bytes("GlobalShare"),GlobalStakeShare()),
            App.localPut(Int(0), Bytes("UserTime"),Global.latest_timestamp()),
            App.globalPut(Bytes("GlobalTime"),Global.latest_timestamp()),
            Transfer(get_stakeasset,unstakeamount),
            
            Return(Int(1))
        ]
    )
    rewardcal1 = ScratchVar(TealType.uint64, 1)
    rewardcal2 = ScratchVar(TealType.uint64, 2)
    claimreward = Seq(
        [
           Assert(Txn.type_enum()==TxnType.ApplicationCall), 
           get_UserTime,
           get_UserShare,
           get_stakedamount_of_sender,
           Assert(get_stakedamount_of_sender.hasValue()),
           rewardcal1.store((get_UserShare.value() + (((get_GlobalTime - get_UserTime.value()))*get_stakedamount_of_sender.value())/Int(86400))/get_GlobalShare),
           rewardcal2.store((rewardcal1.load()*get_RewardPool)/Int(1000000)),
           Transfer(get_Rewardasset,rewardcal2.load()),
           App.globalPut(Bytes("RewardPool"),get_RewardPool - rewardcal2.load()),
           UserStakeShare,
           App.globalPut(Bytes("GlobalShare"),GlobalStakeShare()),
           App.globalPut(Bytes("GlobalTime"),Global.latest_timestamp()),
           App.localPut(Int(0), Bytes("UserTime"),Global.latest_timestamp()),
           Return(Int(1))
        ]
    )

    program = Cond(
        [Txn.application_id() == Int(0), on_creation],    
        [Txn.on_completion() == OnComplete.DeleteApplication, check_creator],
        [Txn.on_completion() == OnComplete.UpdateApplication, update],
        [Txn.on_completion() == OnComplete.CloseOut, on_closeout],
        [Txn.on_completion() == OnComplete.OptIn, appopt_in],
        [Txn.application_args[0] == Bytes("OPTIN"),Optin],
        [Txn.application_args[0] == Bytes("STAKE"), Stake],
        [Txn.application_args[0] == Bytes("UNSTAKE"), Unstake],
        [Txn.application_args[0] == Bytes("CLAIMREWARD"), claimreward],
        # [Txn.application_args[0] == Bytes("reclaim"), reclaim],
    )

    return program


def clear_state_program():
    program = Seq(
        [
            Return(Int(1)),
        ]
    )

    return program

print(compileTeal(approval_program(), mode=Mode.Application, version=5))
print(compileTeal(clear_state_program(), mode=Mode.Application, version=5))
