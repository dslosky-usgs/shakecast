import { Component,
         OnInit, 
         OnDestroy,
         trigger,
         state,
         style,
         transition,
         animate } from '@angular/core';
import { TitleService } from '../../../title/title.service';
import { GroupService } from './group.service'

@Component({
    selector: 'groups',
    templateUrl: './groups.component.html',
    styleUrls: ['./groups.component.css',
                  '../../../shared/css/data-list.css'], 
})
export class GroupsComponent implements OnInit {
    constructor(private groupService: GroupService,
                private titleService: TitleService) {}

    ngOnInit() {
        this.titleService.title.next('Groups')
        //this.groupService.clearMap();
    }

    deleteCurrentGroup() {
        this.groupService.deleteGroups([this.groupService.current_group]);
    }
}