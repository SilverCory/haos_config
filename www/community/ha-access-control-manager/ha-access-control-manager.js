import {
    LitElement,
    html,
    css,
} from "https://unpkg.com/lit-element@2.4.0/lit-element.js?module";

class AccessControlManager extends LitElement {
    static get properties() {
        return {
            hass: { type: Object },
            narrow: { type: Boolean },
            route: { type: Object },
            panel: { type: Object },
            users: { type: Array },
            tableHeaders: { type: Array },
            tableData: { type: Array },
            dataUsers: { type: Array },
            dataGroups: { type: Array },
            isAnUser: { type: Boolean },
            selected: { type: Object },
            needToSetPermissions: { type: Boolean },
            newGroupName: { type: String },
            openCreateGroup: { type: Boolean },
            searchTerm: { type: String },
            _isLoading: { type: Boolean }
        };
    }

    constructor() {
        super();
        this.users = [];
        this.tableHeaders = ["name", "read", "write"];
        this.tableHeadersEntities = ["name", "entity_id", "read", "write"];
        this.tableData = [];
        this.dataUsers = [];
        this.dataGroups = [];
        this.isAnUser = false;
        this.needToFetch = true;
        this.selected = {};
        this.needToSetPermissions = false;
        this.newGroupName = '';
        this.openCreateGroup = false;
        this.expandedDevices = new Set();
        this.searchTerm = '';
        this._isLoading = false;
        this.searchTimeout = null;
    }

    translate(key) {
        return this.hass.localize(`component.ha_access_control_manager.entity.frontend.${key}.name`);
    }    

    update(changedProperties) {
        if (changedProperties.has('hass') && this.hass && this.needToFetch) {
            this.fetchUsers();
            this.fetchAuths();
            this.fetchDevices();
            this.needToFetch = false;
        }
        super.update(changedProperties);
    }

    fetchUsers() {
        this.hass.callWS({ type: 'ha_access_control/list_users' }).then(users => {
            this.users = users;
        });
    }

    fetchDevices() {
        this.hass.callWS({ type: 'ha_access_control/list_devices' }).then(devices => {
            devices.forEach(device => {
                this.tableData.push({
                    entities: device.entities,
                    name: device.name,
                    id: device.id,
                    read: false,
                    write: false
                });
            })
            // this.requestUpdate();
        });
    }

    fetchAuths() {
        this.hass.callWS({ type: 'ha_access_control/list_auths' }).then(data => {
            this.loadAuths(data);
        });
    }

    loadAuths(data) {
        this.dataGroups = data.groups;

        const users = data.users;

        users.forEach(user => {
            if (!user.policy?.entities) {
                user.policy = {
                    entities: {
                        entity_ids: {}
                    }
                }
            }

            // Add group policies to user, but maybe for for later
            // I need to find a way to differentiate between user and group policies when saving an user
            /*
            user.group_ids.forEach(groupId => {
                console.log(groupId, data.groups);
                const group = data.groups.find(group => group.id === groupId);
                if (group.policy?.entities?.entity_ids) {
                    const keys = Object.keys(group.policy.entities.entity_ids);
                    keys.forEach(entityId => {
                        user.policy.entities.entity_ids[entityId] = group.policy.entities.entity_ids[entityId];
                    });
                }
            });*/
        });

        this.dataUsers = users;
        this.displayCustomGroupWarning();
    }

    changeUser(e) {
        const userId = e.detail.value;
        const user = this.dataUsers.find(user => user.id === userId);
        this.selected = user;
        this.isAnUser = true;
    }

    changeGroup(e) {
        const groupId = e.detail.value;
        const group = this.dataGroups.find(group => group.id === groupId);
        this.selected = group;
        this.isAnUser = false;
        this.loadData(group);
    }

    loadData(data) {
        let allTrueRW = false;
        let allTrueRead = false;
        if (data.id === 'system-users' || data.id === 'system-admin') {
            allTrueRW = true;
        }

        if (data.id === 'system-read-only') {
            allTrueRead = true;
        }

        this.tableData.forEach(device => {
            device.entities.forEach(entity => {
                if (allTrueRW) {
                    entity.read = true;
                    entity.write = true;
                    return;
                }

                if (allTrueRead) {
                    entity.read = true;
                    entity.write = false;
                    return;
                }

                if(data.policy?.entities?.entity_ids[entity.entity_id]) {
                    entity.read = data.policy.entities.entity_ids[entity.entity_id] ? true : false;
                    entity.write = data.policy.entities.entity_ids[entity.entity_id] && typeof data.policy.entities.entity_ids[entity.entity_id] !== 'object' ? true : false;
                } else {
                    entity.read = false;
                    entity.write = false;
                }
            });

            const entityReads = device.entities.map(entity => entity.read);
            const entityWrites = device.entities.map(entity => entity.write);

            device.read = entityReads.every(val => val === true) ? true : entityReads.some(val => val === true) ? "indeterminate" : false;
            device.write = entityWrites.every(val => val === true) ? true : entityWrites.some(val => val === true) ? "indeterminate" : false;

        });
        this.tableData = [...this.tableData];
        this.requestUpdate();
    }

    handleCheckboxChange(groupId, checked) {
        if (checked) {
            this.selected.group_ids.push(groupId);
        } else {
            this.selected.group_ids = this.selected.group_ids.filter(id => id !== groupId);
        }  
        
    }

    handleNewGroupSave() {
        const inputField = this.shadowRoot.querySelector('.group-input');
        if (!inputField.reportValidity()) {
            return; 
        }

        const name = this.newGroupName.trim();
        if (name) {
            const id = `custom-group-${name.toLowerCase().replaceAll(' ', '-')}`;
            const newGroup = { id, name };
            this.dataGroups = [...this.dataGroups, newGroup];
            this.hass.callWS({ type: 'ha_access_control/set_auths', isAnUser: false, data: newGroup }).then(data => {
                this.loadAuths(data);
            })
            this.newGroupName = '';
        }
        this.needToSetPermissions = true;
    }
    
    handleNewGroupInput(e) {
        this.newGroupName = e.target.value;
    }

    handleSearchInput(e) {
        this.searchTerm = e.target.value;
        this._isLoading = true;
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => {
            this._isLoading = false;
        }, 500);
    }

    get processedTableData() {
        console.log("Processing table data with search term:", this.searchTerm);
        
        const searchTermLower = this.searchTerm ? this.searchTerm.toLowerCase() : null;
    
        if (!searchTermLower) {
            return this.tableData.map(device => ({
                ...device,
                displayEntities: device.entities,
                isExpanded: this.expandedDevices.has(device.id)
            }));
        }
    
        return this.tableData.map(device => {
            const deviceNameMatch = device.name.toLowerCase().includes(searchTermLower);
    
            const matchingEntities = device.entities.filter(entity =>
                (entity.name && entity.name.toLowerCase().includes(searchTermLower)) ||
                (entity.original_name && entity.original_name.toLowerCase().includes(searchTermLower)) ||
   