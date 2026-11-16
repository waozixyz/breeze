#include "ziran_host.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int action, click, audio_state, starts, stops, volume, selected;
static char station[256], saved_station[256], saved_volume[8], drawn[4096];
static VmHostField message[3], frame[6], scroll[2], rectangle[4], pointer[5];
static int view_width=400, view_height=800, pointer_down, pointer_pressed, pointer_released;
static double pointer_x, pointer_y;
static double power_x, power_y, volume_x, volume_y, tuning_x, tuning_y;
static char account[32]="radio-test-account";

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
        message[2]=(VmHostField){"account",text(account)};
        *out=record("AppMessage",message,3); return 1;
    }
    if(!strcmp(name,"WriteAppHost")) {
        assert(count==1 && field(args[0],"succeeded").integer); return 1;
    }
    if(!strcmp(name,"ReadAppUiHost")) {
        frame[0]=(VmHostField){"width",integer("s32",view_width)};
        frame[1]=(VmHostField){"height",integer("s32",view_height)};
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
    if(!strcmp(name,"ImageHostedHost")) {
        char asset[128]; copy(asset,sizeof(asset),field(args[1],"asset_path"));
        assert(!strcmp(asset,"assets/radio/player.avif"));
        int expected = view_width - 32;
        if(expected > 620) expected = 620;
        assert(field(field(args[1],"bounds"),"height").real == expected);
        return 1;
    }
    if(!strcmp(name,"BoxHostedHost")) { *out=integer("s32",0); return 1; }
    if(!strcmp(name,"PollPointer")) {
        pointer[0]=(VmHostField){"x",{.kind=VM_HOST_REAL,.type="float32",.real=pointer_x}};
        pointer[1]=(VmHostField){"y",{.kind=VM_HOST_REAL,.type="float32",.real=pointer_y}};
        pointer[2]=(VmHostField){"down",integer("bool",pointer_down)};
        pointer[3]=(VmHostField){"pressed",integer("bool",pointer_pressed)};
        pointer[4]=(VmHostField){"released",integer("bool",pointer_released)};
        *out=record("PointerFrame",pointer,5); return 1;
    }
    if(!strcmp(name,"TextHostedHost")) {
        char label[512]; copy(label,sizeof(label),field(args[1],"text"));
        assert(strlen(drawn)+strlen(label)+2<sizeof(drawn));
        strcat(drawn,label); strcat(drawn,"\n"); return 1;
    }
    if(!strcmp(name,"ButtonHostedHost")) {
        int id=field(args[1],"id").integer;
        VmHostValue bounds=field(args[1],"bounds");
        assert(field(bounds,"width").real>=44 && field(bounds,"height").real>=44);
        assert(field(bounds,"x").real>=0 && field(bounds,"x").real+field(bounds,"width").real<=view_width);
        if (id == 26002) {
            power_x = field(bounds, "x").real + field(bounds, "width").real / 2;
            power_y = field(bounds, "y").real + field(bounds, "height").real / 2;
        }
        if (id == 26003) {
            volume_x = field(bounds, "x").real + field(bounds, "width").real / 2;
            volume_y = field(bounds, "y").real + field(bounds, "height").real / 2;
        }
        if (id == 26005) {
            tuning_x = field(bounds, "x").real + field(bounds, "width").real / 2;
            tuning_y = field(bounds, "y").real + field(bounds, "height").real / 2;
        }
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
    click=26003; run(instance,2); assert(volume==65 && !strcmp(saved_volume,"65"));
    click=26011; run(instance,2);
    assert(starts==2 && volume==65 && strstr(station,"/ama-s"));
    assert(!strcmp(saved_station,station));
    click=26002; run(instance,2); assert(stops==1 && audio_state==0);
    BundleInstanceClose(instance);
    instance=BundleInstantiate(bundle,bindings,count); assert(instance);
    BundleInstanceMatchFieldsByName(instance,1);
    run(instance,2); assert(starts==2 && selected==26011);
    assert(strstr(drawn,"65"));
    click=26002; run(instance,2); assert(starts==3 && volume==65 && strstr(station,"/ama-s"));
    // Dragging changes volume without toggling audio on button release.
    for (int layout = 0; layout < 2; layout++) {
        view_width = layout ? 1280 : 390;
        run(instance, 2);
        int prior_starts = starts;
        int prior_stops = stops;
        assert(power_x != volume_x || power_y != volume_y);
        pointer_x = volume_x;
        pointer_y = volume_y;
        pointer_pressed = pointer_down = 1;
        run(instance, 2);
        pointer_pressed = 0;
        pointer_y -= 200;
        run(instance, 2);
        assert(volume == 100 && !strcmp(saved_volume, "100"));
        pointer_released = 1;
        pointer_down = 0;
        click = 26003;
        run(instance, 2);
        assert(starts == prior_starts && stops == prior_stops &&
            audio_state > 0 && volume == 100);
        pointer_released = 0;

        click = 26010;
        run(instance, 2);
        run(instance, 2);
        pointer_x = tuning_x;
        pointer_y = tuning_y;
        pointer_pressed = pointer_down = 1;
        run(instance, 2);
        pointer_pressed = 0;
        pointer_x += 56;
        run(instance, 2);
        prior_starts = starts;
        pointer_released = 1;
        pointer_down = 0;
        click = 26005;
        run(instance, 2);
        pointer_released = 0;
        run(instance, 2);
        assert(starts == prior_starts && selected == 26012);
        click = 26002;
        run(instance, 2);
        prior_starts = starts;
        click = 26005;
        run(instance, 2);
        run(instance, 2);
        assert(starts == prior_starts && audio_state == 0 && selected == 26010);
        click = 26002;
        run(instance, 2);
    }
    // Account changes reload records and reject malformed saved values.
    strcpy(account, "other-account");
    strcpy(saved_volume, "bad");
    strcpy(saved_station, "https://invalid.example/");
    run(instance, 2);
    assert(selected == 26010 && strstr(drawn, "60"));
    click = 26002;
    run(instance, 2);
    click = 26002;
    run(instance, 2);
    assert(volume == 60 && strstr(station, "/asp-s"));
    BundleInstanceClose(instance); BundleClose(bundle);
    puts("radio.zx: identity, station choices, separate power and volume, tuning and saved preferences passed.");
    return 0;
}
