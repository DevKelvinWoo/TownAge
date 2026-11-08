#include "TownAgeDoorAnimInstance.h"

#include "Animation/AnimSingleNodeInstanceProxy.h"

namespace
{
/** Engine's proxy access synchronizes the game-thread asset setter with evaluation. */
struct FTownAgeDoorAnimProxy final : FAnimSingleNodeInstanceProxy
{
    explicit FTownAgeDoorAnimProxy(UAnimInstance* Instance)
        : FAnimSingleNodeInstanceProxy(Instance)
    {
    }

    virtual void Initialize(UAnimInstance* Instance) override
    {
        FAnimSingleNodeInstanceProxy::Initialize(Instance);
        ResetPoseCache();
        LastRequestedAsset.Reset();
    }

    virtual void PreUpdate(UAnimInstance* Instance, float DeltaSeconds) override
    {
        FAnimSingleNodeInstanceProxy::PreUpdate(Instance, DeltaSeconds);
        const float RequestedDuration = CastChecked<UTownAgeDoorAnimInstance>(Instance)->AssetBlendDuration;
        BlendDuration = FMath::IsFinite(RequestedDuration) ? FMath::Clamp(RequestedDuration, 0.f, 1.f) : .22f;
    }

    virtual void SetAnimationAsset(UAnimationAsset* NewAsset, USkeletalMeshComponent* MeshComponent,
        bool bIsLooping, float InPlayRate) override
    {
        if (LastRequestedAsset.Get() != NewAsset)
        {
            // An interrupted transition starts from the composed result of the
            // previous frame, rather than jumping back to an older source pose.
            BlendFromPose = LastEvaluatedPose;
            BlendFromBoneSerial = LastEvaluatedBoneSerial;
            BlendElapsed = 0.f;
            LastRequestedAsset = NewAsset;
        }
        FAnimSingleNodeInstanceProxy::SetAnimationAsset(NewAsset, MeshComponent, bIsLooping, InPlayRate);
    }

    virtual void UpdateAnimationNode(const FAnimationUpdateContext& Context) override
    {
        if (!BlendFromPose.IsEmpty())
            BlendElapsed = FMath::Min(BlendElapsed + FMath::Max(0.f, Context.GetDeltaTime()), BlendDuration);
        FAnimSingleNodeInstanceProxy::UpdateAnimationNode(Context);
    }

    virtual bool Evaluate(FPoseContext& Output) override
    {
        const bool bEvaluated = FAnimSingleNodeInstanceProxy::Evaluate(Output);
        const int32 BoneCount = Output.Pose.GetNumBones();
        if (!bEvaluated || !CurrentAsset || BoneCount == 0)
        {
            ResetPoseCache();
            return bEvaluated;
        }

        const uint16 BoneSerial = Output.Pose.GetBoneContainer().GetSerialNumber();
        const bool bMatchingBones = BlendFromPose.Num() == BoneCount && BlendFromBoneSerial == BoneSerial;
        if (!BlendFromPose.IsEmpty() && (!bMatchingBones || BlendDuration <= SMALL_NUMBER))
            BlendFromPose.Reset();

        if (!BlendFromPose.IsEmpty())
        {
            const float TimeFraction = FMath::Clamp(BlendElapsed / BlendDuration, 0.f, 1.f);
            const float Weight = TimeFraction * TimeFraction * (3.f - 2.f * TimeFraction);
            for (FCompactPoseBoneIndex BoneIndex : Output.Pose.ForEachBoneIndex())
            {
                FTransform& Target = Output.Pose[BoneIndex];
                Target.Blend(BlendFromPose[BoneIndex.GetInt()], Target, Weight);
                Target.NormalizeRotation();
            }
            if (TimeFraction >= 1.f)
                BlendFromPose.Reset();
        }

        // Only bone transforms are blended. Keep the new asset's evaluated
        // curves and custom attributes intact (the current door clips have none).
        LastEvaluatedPose = Output.Pose.GetBones();
        LastEvaluatedBoneSerial = BoneSerial;
        return bEvaluated;
    }

private:
    void ResetPoseCache()
    {
        LastEvaluatedPose.Reset();
        BlendFromPose.Reset();
        LastEvaluatedBoneSerial = 0;
        BlendFromBoneSerial = 0;
        BlendElapsed = 0.f;
    }

    TWeakObjectPtr<UAnimationAsset> LastRequestedAsset;
    TArray<FTransform> LastEvaluatedPose;
    TArray<FTransform> BlendFromPose;
    uint16 LastEvaluatedBoneSerial = 0;
    uint16 BlendFromBoneSerial = 0;
    float BlendElapsed = 0.f;
    float BlendDuration = .22f;
};
}

UTownAgeDoorAnimInstance::UTownAgeDoorAnimInstance(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
}

FAnimInstanceProxy* UTownAgeDoorAnimInstance::CreateAnimInstanceProxy()
{
    return new FTownAgeDoorAnimProxy(this);
}
