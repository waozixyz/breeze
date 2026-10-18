#include "ziran_host.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int action, click, audio_state, starts, stops, volume, selected;
static char station[256], saved_station[256], saved_volume[8], drawn[4096];
static VmHostField message[2], frame[6], scroll[2], rectangle[4];

static VmHostValue integer(const char *type, int value) {
    return (VmHostValue){.kind=VM_HOST_INTEGER, .type=type, .integer=value};
}
static VmHostValue text(const char *value) {
    return (VmHostValue){.kind=VM_HOST_STRING, .type="string",
        .data=(const unsigned char *)value, .length=strlen(value)};
}
static VmHostValue record(const char *type, VmHostField *fields, int count) {
    return (VmHostValue){.kind=VM_HOST_RECORD, .type=type, .fields=fields, .field_count=count};
}
static VmHostValue field(VmHostValue record, const char *name) {
    for(size_t i=0; i<record.field_count; i++)
        if(!strcmp(record.fields[i].name,name)) return record.fields[i].value;
    return (VmHostValue){0};
}
static void copy(char *out, size_t capacity, VmHostValue value) {
    assert(value.kind==VM_HOST_STRING && value.length<capacity);
    memcpy(out,value.data,value.length); out[value.length]=0;
}
static int host(void *context, const char *module, const char *name,
    const VmHostValue *args, int count, VmHostValue *out) {
    (void)context; (void)module;
    if(!strcmp(name,"ReadAppHost")) {
        message[0]=(VmHostField){"abi",integer("s32",2)};
        message[1]=(VmHostField){"action",integer("s32",action)};
        *out=record("AppMessage",message,2); return 1;
    }
    if(!strcmp(name,"WriteAppHost")) {
        assert(count==1 && field(args[0],"succeeded").integer); return 1;
    }
    if(!strcmp(name,"ReadAppUiHost")) {
        frame[0]=(VmHostField){"width",integer("s32",400)};
        frame[1]=(VmHostField){"height",integer("s32",800)};
        frame[2]=(VmHostField){"font",integer("s32",18)};
        frame[3]=(VmHostField){"scale",{.kind=VM_HOST_REAL,.type="float32",.real=1}};
        frame[4]=(VmHostField){"top",integer("s32",32)};
        frame[5]=(VmHostField){"bottom",integer("s32",0)};
        *out=record("AppUiFrame",frame,6); return 1;
    }
    if(!strcmp(name,"AppLocaleHost")) { *out=args[0]; return 1; }
    if(!strcmp(name,"AppRecordHost")) {
        char key[32]; copy(key,sizeof(key),args[0]);
        *out=text(!strcmp(key,"station")?saved_station:saved_volume); return 1;
    }
    if(!strcmp(name,"SaveAppRecordHost")) {
        char key[32]; copy(key,sizeof(key),args[0]);
        if(!strcmp(key,"station")) copy(saved_station,sizeof(saved_station),args[1]);
        else { assert(!strcmp(key,"volume")); copy(saved_volume,sizeof(saved_volume),args[1]); }
        *out=integer("bool",1); return 1;
    }
    if(!strcmp(name,"AudioStateHost")) { *out=integer("s32",audio_state); return 1; }
    if(!strcmp(name,"AudioStartHost")) {
        copy(station,sizeof(station),args[0]);
        assert(!strncmp(station,"https://radio.stereoscenic.com/",30));
        starts++; audio_state=1; *out=integer("bool",1); return 1;
    }
    if(!strcmp(name,"AudioStopHost")) {
        stops++; audio_state=0; *out=integer("bool",1); return 1;
    }
    if(!strcmp(name,"AudioVolumeHost")) {
        volume=args[0].integer; assert(volume>=0 && volume<=100);
        *out=integer("bool",1); return 1;
    }
    if(!strcmp(name,"TextHostedHost")) {
        char label[512]; copy(label,sizeof(label),field(args[1],"text"));
        assert(strlen(drawn)+strlen(label)+2<sizeof(drawn));
        strcat(drawn,label); strcat(drawn,"\n"); return 1;
    }
    if(!strcmp(name,"ButtonHostedHost")) {
        int id=field(args[1],"id").integer;
        if(id>=26010 && id<26013 && field(args[1],"selected").integer) selected=id;
        int hit=click==id && !field(args[1],"disabled").integer;
        if(hit) click=0;
        *out=integer("s32",hit); return 1;
    }
    if(!strcmp(name,"ScrollHostedHost")) {
        scroll[0]=(VmHostField){"opened",integer("bool",1)};
        const char *names[]={"x","y","width","height"};
        VmHostValue bounds=field(args[1],"bounds");
        for(int i=0;i<4;i++) rectangle[i]=(VmHostField){names[i],
            {.kind=VM_HOST_REAL,.type="float32",.real=field(bounds,names[i]).real}};
        scroll[1]=(VmHostField){"content",record("Rectangle",rectangle,4)};
        *out=record("ScrollResult",scroll,2); return 1;
    }
    if(!strcmp(name,"EndHostedHost")) { *out=integer("bool",1); return 1; }
    fprintf(stderr,"Unexpected radio capability %s.%s\n",module,name); return 0;
}
static void run(BundleInstance *instance, int next_action) {
    action=next_action; drawn[0]=0;
    long long answer; int has_answer;
    assert(BundleInstanceRun(instance,&answer,&has_answer));
    assert(has_answer && answer==(action==0?8:0));
}

int main(int argc,char **argv) {
    assert(argc==2);
    Bundle *bundle=BundleOpen(argv[1]); assert(bundle);
    size_t count=BundleCapabilityCount(bundle); assert(count>10 && count<64);
    HostBinding bindings[64];
    for(size_t i=0;i<count;i++) {
        bindings[i]=(HostBinding){BundleCapabilityModule(bundle,i),
            BundleCapabilityFunction(bundle,i),host,NULL};
        assert(!strstr(bindings[i].function,"Uri"));
    }
    BundleInstance *instance=BundleInstantiate(bundle,bindings,count); assert(instance);
    BundleInstanceMatchFieldsByName(instance,1);
    run(instance,0); run(instance,1); run(instance,2);
    assert(starts==0 && selected==26010 && strstr(drawn,"radio_stopped"));
    click=26002; run(instance,2);
    assert(starts==1 && volume==60 && strstr(station,"/asp-s"));
    audio_state=2; run(instance,1); assert(stops==0 && audio_state==2);
    click=26003; run(instance,2); assert(volume==55 && !strcmp(saved_volume,"55"));
    click=26011; run(instance,2);
    assert(starts==2 && volume==55 && strstr(station,"/ama-s"));
    assert(!strcmp(saved_station,station));
    click=26002; run(instance,2); assert(stops==1 && audio_state==0);
    BundleInstanceClose(instance);
    instance=BundleInstantiate(bundle,bindings,count); assert(instance);
    BundleInstanceMatchFieldsByName(instance,1);
    run(instance,2); assert(starts==2 && selected==26011);
    assert(strstr(drawn,"55"));
    click=26002; run(instance,2); assert(starts==3 && volume==55 && strstr(station,"/ama-s"));
    BundleInstanceClose(instance); BundleClose(bundle);
    puts("radio.zib: identity, station choices, playback, independent volume, navigation and saved preferences passed.");
    return 0;
}
